from __future__ import annotations

import io
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
        import pyaudio

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

        logger.info(
            "Starting audio capture",
            extra={
                "device": dev_name,
                "sample_rate": sr,
                "channels": channels,
                "frame_size": frames_per_buffer,
            },
        )

        def pa_callback(in_data, frame_count, time_info, status):
            try:
                audio = np.frombuffer(in_data, dtype=np.int16).reshape(-1, channels)
                if channels > 1 and config.channels == 1:
                    audio = audio.mean(axis=1)
                if self._running and callback:
                    callback(audio)
            except Exception:
                logger.exception("Audio callback error")
            return (None, pyaudio.paContinue)

        try:
            self._stream = pa.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=sr,
                input=True,
                input_device_index=dev_index,
                frames_per_buffer=frames_per_buffer,
                stream_callback=pa_callback,
            )
            self._stream.start_stream()
            self._running = True
            self._sample_rate = sr
        except Exception as e:
            raise AudioStreamError(f"Failed to open audio stream: {e}") from e

    def close_stream(self) -> None:
        self._running = False
        if self._stream:
            try:
                if self._stream.is_active():
                    self._stream.stop_stream()
                self._stream.close()
            except Exception as e:
                logger.warning("Error closing audio stream", exc_info=e)
            self._stream = None
        logger.info("Audio capture stopped")

    @property
    def is_running(self) -> bool:
        return self._running

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
    def play_wav(data: bytes, device_index: int = -1) -> None:
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
