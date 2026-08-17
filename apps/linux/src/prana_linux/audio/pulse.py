from __future__ import annotations

import io
import re
import shutil
import subprocess
import threading
import wave
from typing import Callable

import numpy as np

from prana_core.audio.base import AudioBackend
from prana_core.audio.exceptions import AudioDeviceNotFoundError, AudioStreamError
from prana_core.config.schema import AudioConfig
from prana_core.common.logger import get_logger

logger = get_logger(__name__)


class PulseBackend(AudioBackend):
    _pa = None
    _pa_lock = threading.Lock()

    def __init__(self):
        self._stream = None
        self._running = False
        self._sample_rate = 0
        self._capture_thread: threading.Thread | None = None

    @property
    def name(self) -> str:
        return "pulse"

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @classmethod
    def _get_pa(cls):
        if cls._pa is None:
            with cls._pa_lock:
                if cls._pa is None:
                    import pyaudio
                    cls._pa = pyaudio.PyAudio()
        return cls._pa

    def open_stream(self, config: AudioConfig, callback: Callable[[np.ndarray], None]) -> None:
        pa = self._get_pa()
        mode = config.capture_mode

        if mode == "loopback":
            logger.warning("Loopback not supported on this platform, falling back to device capture")
            mode = "device"

        device_info = self._resolve_device(config, pa)

        dev_index = device_info["index"]
        dev_name = device_info["name"]
        sr = int(device_info["defaultSampleRate"])
        channels = min(config.channels, device_info["maxInputChannels"])
        if channels < 1:
            channels = device_info["maxInputChannels"]

        frames_per_buffer = config.frame_size
        alsa_device = self._alsa_device_name(device_info)
        arecord = shutil.which("arecord")
        if arecord is None:
            raise AudioStreamError("arecord is required for Linux audio capture")

        logger.info(
            "Starting audio capture",
            extra={
                "device": dev_name,
                "sample_rate": sr,
                "channels": channels,
                "frame_size": frames_per_buffer,
                "alsa_device": alsa_device,
            },
        )

        try:
            self._stream = subprocess.Popen(
                [
                    arecord,
                    "-q",
                    "-D",
                    alsa_device,
                    "-t",
                    "raw",
                    "-f",
                    "S16_LE",
                    "-c",
                    str(channels),
                    "-r",
                    str(sr),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self._running = True
            self._sample_rate = sr
            self._capture_thread = threading.Thread(
                target=self._read_capture,
                args=(callback, channels, frames_per_buffer),
                name="prana-alsa-capture",
                daemon=True,
            )
            self._capture_thread.start()
        except Exception as e:
            raise AudioStreamError(f"Failed to open audio stream: {e}") from e

    def close_stream(self) -> None:
        self._running = False
        if self._stream:
            try:
                self._stream.terminate()
                self._stream.wait(timeout=3.0)
            except Exception as e:
                logger.warning("Error closing audio stream", exc_info=e)
                try:
                    self._stream.kill()
                except Exception:
                    pass
            if self._stream.stdout is not None:
                self._stream.stdout.close()
            if self._stream.stderr is not None:
                self._stream.stderr.close()
            self._stream = None
        if self._capture_thread is not None:
            self._capture_thread.join(timeout=3.0)
            self._capture_thread = None
        logger.info("Audio capture stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    @staticmethod
    def _alsa_device_name(device_info: dict) -> str:
        match = re.search(r"\(hw:(\d+),(\d+)\)", str(device_info.get("name", "")))
        if match is None:
            raise AudioDeviceNotFoundError(
                f"Cannot resolve ALSA hardware device from {device_info.get('name', '')}"
            )
        return f"hw:{match.group(1)},{match.group(2)}"

    def _read_capture(
        self,
        callback: Callable[[np.ndarray], None],
        channels: int,
        frames_per_buffer: int,
    ) -> None:
        process = self._stream
        if process is None or process.stdout is None:
            return
        bytes_per_chunk = frames_per_buffer * channels * 2
        pending = bytearray()
        try:
            while self._running:
                data = process.stdout.read(bytes_per_chunk - len(pending))
                if not data:
                    break
                pending.extend(data)
                if len(pending) < bytes_per_chunk:
                    continue
                audio = np.frombuffer(bytes(pending), dtype="<i2").reshape(
                    -1, channels
                )
                pending.clear()
                if channels > 1:
                    audio = audio.mean(axis=1).astype(np.int16)
                callback(audio)
        except Exception:
            if self._running:
                logger.exception("ALSA capture reader failed")
        finally:
            if self._running:
                error = ""
                if process.stderr is not None:
                    error = process.stderr.read().decode(errors="replace").strip()
                logger.error(
                    "ALSA capture process stopped unexpectedly",
                    extra={"return_code": process.poll(), "error": error},
                )
                self._running = False

    def _resolve_device(self, config: AudioConfig, pa) -> dict:
        idx = config.device_index

        if idx >= 0:
            try:
                info = pa.get_device_info_by_index(idx)
                if info["maxInputChannels"] > 0:
                    return info
                raise AudioDeviceNotFoundError(
                    f"Device [{idx}] {info['name']} has no input channels"
                )
            except AudioDeviceNotFoundError:
                raise
            except Exception as e:
                raise AudioDeviceNotFoundError(
                    f"Device index {idx} not found: {e}"
                ) from e

        count = pa.get_device_count()
        for i in range(count):
            try:
                info = pa.get_device_info_by_index(i)
                if info["maxInputChannels"] > 0:
                    logger.info("Using default input device", extra={"device": info["name"]})
                    return info
            except Exception:
                continue

        raise AudioDeviceNotFoundError("No input device found")

    @staticmethod
    def list_devices() -> list[dict]:
        import pyaudio

        pa = pyaudio.PyAudio()
        try:
            count = pa.get_device_count()
            devices = []
            for i in range(count):
                info = pa.get_device_info_by_index(i)
                host_api = pa.get_host_api_info_by_index(info["hostApi"])
                devices.append(
                    {
                        "index": i,
                        "name": info["name"],
                        "inputs": info["maxInputChannels"],
                        "outputs": info["maxOutputChannels"],
                        "sr": info["defaultSampleRate"],
                        "host_api": host_api["name"],
                    }
                )
            return devices
        finally:
            pa.terminate()

    @staticmethod
    def play_wav(
        data: bytes,
        device_index: int = -1,
        stop_event: threading.Event | None = None,
    ) -> None:
        import pyaudio

        try:
            source = wave.open(io.BytesIO(data), "rb")
        except (EOFError, wave.Error) as exc:
            raise AudioStreamError(f"Invalid TX WAV audio: {exc}") from exc

        with source:
            pa = pyaudio.PyAudio()
            stream = None
            try:
                sample_width = source.getsampwidth()
                channels = source.getnchannels()
                source_rate = source.getframerate()

                if sample_width != 2:
                    raise AudioStreamError("TX WAV must use 16-bit PCM audio")

                if device_index >= 0:
                    info = pa.get_device_info_by_index(device_index)
                    if int(info.get("maxOutputChannels", 0)) < 1:
                        raise AudioDeviceNotFoundError(
                            "Selected TX device has no output channels"
                        )
                else:
                    info = pa.get_default_output_device_info()

                output_rate = int(info.get("defaultSampleRate", source_rate))
                frames = source.readframes(source.getnframes())
                if output_rate != source_rate and frames:
                    samples = np.frombuffer(frames, dtype="<i2").reshape(-1, channels)
                    output_count = max(
                        1, round(samples.shape[0] * output_rate / source_rate)
                    )
                    source_positions = np.arange(samples.shape[0], dtype=np.float64)
                    output_positions = np.linspace(
                        0, samples.shape[0] - 1, output_count
                    )
                    resampled = np.empty((output_count, channels), dtype=np.int16)
                    for channel in range(channels):
                        resampled[:, channel] = np.clip(
                            np.rint(
                                np.interp(
                                    output_positions,
                                    source_positions,
                                    samples[:, channel],
                                )
                            ),
                            -32768,
                            32767,
                        ).astype(np.int16)
                    frames = resampled.astype("<i2", copy=False).tobytes()

                kwargs = {
                    "format": pa.get_format_from_width(sample_width),
                    "channels": channels,
                    "rate": output_rate,
                    "output": True,
                }
                if device_index >= 0:
                    kwargs["output_device_index"] = device_index
                stream = pa.open(**kwargs)
                bytes_per_frame = sample_width * channels
                chunk_size = 4096 * bytes_per_frame
                for offset in range(0, len(frames), chunk_size):
                    if stop_event is not None and stop_event.is_set():
                        break
                    stream.write(frames[offset : offset + chunk_size])
            except AudioDeviceNotFoundError:
                raise
            except Exception as exc:
                raise AudioStreamError(f"Failed to play TX audio: {exc}") from exc
            finally:
                if stream is not None:
                    stream.stop_stream()
                    stream.close()
                pa.terminate()
