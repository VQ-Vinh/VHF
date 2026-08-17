from __future__ import annotations

from typing import Callable
import threading
import io
import wave

import numpy as np

from prana_core.audio.base import AudioBackend
from prana_core.audio.exceptions import AudioDeviceNotFoundError, AudioStreamError
from prana_core.config.schema import AudioConfig
from prana_core.common.logger import get_logger

logger = get_logger(__name__)


class WASAPIBackend(AudioBackend):
    _loopback_identity_by_index: dict[int, tuple[str, int, int]] = {}

    def __init__(self):
        self._pa = None
        self._stream = None
        self._running = False
        self._sample_rate = 0

    @property
    def name(self) -> str:
        return "wasapi"

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @staticmethod
    def _new_pa():
        import pyaudiowpatch as paw

        return paw.PyAudio()

    def open_stream(self, config: AudioConfig, callback: Callable[[np.ndarray], None]) -> None:
        import pyaudiowpatch as paw

        # PortAudio/WASAPI instances are thread-affine on some Windows audio
        # drivers. They can also conflict when a discovery instance remains
        # alive while capture starts, so capability scans always terminate
        # their own instance before the pipeline creates this one.
        pa = paw.PyAudio()
        self._pa = pa

        def pa_callback(in_data, frame_count, time_info, status):
            try:
                audio = np.frombuffer(in_data, dtype=np.int16).reshape(-1, channels)
                if channels > 1 and config.channels == 1:
                    audio = audio.mean(axis=1)
                energy = float(np.sqrt(np.mean(audio.astype(np.float32) ** 2)))
                logger.debug("Audio callback: frames=%d energy=%.1f max=%d", frame_count, energy, int(np.max(np.abs(audio))))
                if self._running and callback:
                    callback(audio)
            except Exception:
                logger.exception("Audio callback error")
            return (None, paw.paContinue)

        try:
            mode = config.capture_mode
            device_info = None
            if mode == "loopback":
                expected = type(self)._loopback_identity_by_index.get(
                    config.device_index
                )
                device_info = self._find_loopback_device(
                    pa,
                    config.device_index,
                    expected_identity=expected,
                )
                if device_info is None:
                    raise AudioDeviceNotFoundError(
                        "No WASAPI loopback device found. "
                        "Try capture_mode = 'device' or select a loopback device."
                    )

            if device_info is None:
                device_info = self._resolve_device(config, pa)

            dev_index = device_info["index"]
            dev_name = device_info["name"]
            sr = int(device_info["defaultSampleRate"])
            channels = min(config.channels, device_info["maxInputChannels"])
            if channels < 1:
                channels = device_info["maxInputChannels"]
            frames_per_buffer = config.frame_size

            if config.dtype != "int16":
                logger.warning(
                    "Only int16 capture supported, got '%s'. Falling back to int16.",
                    config.dtype,
                )

            logger.info(
                "Starting audio capture",
                extra={
                    "device": dev_name,
                    "sample_rate": sr,
                    "channels": channels,
                    "frame_size": frames_per_buffer,
                    "capture_mode": mode,
                },
            )
            self._stream = pa.open(
                format=paw.paInt16,
                channels=channels,
                rate=sr,
                input=True,
                input_device_index=dev_index,
                frames_per_buffer=frames_per_buffer,
                stream_callback=pa_callback,
            )
            self._running = True
            self._sample_rate = sr
        except AudioDeviceNotFoundError:
            pa.terminate()
            self._pa = None
            raise
        except Exception as e:
            pa.terminate()
            self._pa = None
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
        if self._pa is not None:
            try:
                self._pa.terminate()
            except Exception as e:
                logger.warning("Error terminating audio backend", exc_info=e)
            self._pa = None
        logger.info("Audio capture stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    @staticmethod
    def _is_loopback_device(info: dict) -> bool:
        return (
            info.get("maxInputChannels", 0) > 0
            and "loopback" in str(info.get("name", "")).lower()
        )

    @staticmethod
    def _device_identity(info: dict) -> tuple[str, int, int]:
        return (
            str(info.get("name", "")),
            int(info.get("maxInputChannels", 0) or 0),
            int(info.get("defaultSampleRate", 0) or 0),
        )

    def _find_loopback_device(
        self,
        pa,
        device_index: int = -1,
        expected_identity: tuple[str, int, int] | None = None,
    ) -> dict | None:
        if device_index >= 0:
            try:
                info = pa.get_device_info_by_index(device_index)
            except Exception as e:
                raise AudioDeviceNotFoundError(
                    f"Loopback device index {device_index} not found: {e}"
                ) from e

            if self._is_loopback_device(info) and (
                expected_identity is None
                or self._device_identity(info) == expected_identity
            ):
                logger.info(
                    "Using selected loopback device",
                    extra={"device": info["name"], "device_index": device_index},
                )
                return info

            if expected_identity is not None:
                for i in range(pa.get_device_count()):
                    candidate = pa.get_device_info_by_index(i)
                    if (
                        self._is_loopback_device(candidate)
                        and self._device_identity(candidate) == expected_identity
                    ):
                        logger.info(
                            "Resolved shifted loopback device index",
                            extra={
                                "device": candidate["name"],
                                "old_device_index": device_index,
                                "device_index": candidate["index"],
                            },
                        )
                        return candidate

            if not self._is_loopback_device(info):
                raise AudioDeviceNotFoundError(
                    f"Device [{device_index}] {info.get('name', 'Unknown')} "
                    "is not a WASAPI loopback input"
                )
            raise AudioDeviceNotFoundError(
                f"Device [{device_index}] {info.get('name', 'Unknown')} "
                "no longer matches the selected WASAPI loopback device"
            )

        count = pa.get_device_count()
        for i in range(count):
            try:
                info = pa.get_device_info_by_index(i)
                if self._is_loopback_device(info):
                    logger.info("Found loopback device", extra={"device": info["name"]})
                    return info
            except Exception:
                continue
        return None

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

    @classmethod
    def list_devices(cls) -> list[dict]:
        pa = cls._new_pa()
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

    @classmethod
    def list_loopback_devices(cls) -> list[dict]:
        pa = cls._new_pa()
        try:
            devices = []
            identities = {}
            for i in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(i)
                if cls._is_loopback_device(info):
                    identities[i] = cls._device_identity(info)
                    host_api = pa.get_host_api_info_by_index(info["hostApi"])
                    devices.append({
                        "index": i,
                        "name": info["name"],
                        "inputs": info["maxInputChannels"],
                        "outputs": info["maxOutputChannels"],
                        "sr": int(info["defaultSampleRate"]),
                        "host_api": host_api["name"],
                    })
            cls._loopback_identity_by_index = identities
            return devices
        finally:
            pa.terminate()

    @classmethod
    def play_wav(
        cls,
        data: bytes,
        device_index: int = -1,
        stop_event: threading.Event | None = None,
    ) -> None:
        import pyaudiowpatch as paw

        with wave.open(io.BytesIO(data), "rb") as source:
            pa = paw.PyAudio()
            stream = None
            try:
                kwargs = {
                    "format": pa.get_format_from_width(source.getsampwidth()),
                    "channels": source.getnchannels(),
                    "rate": source.getframerate(),
                    "output": True,
                }
                if device_index >= 0:
                    info = pa.get_device_info_by_index(device_index)
                    if int(info.get("maxOutputChannels", 0)) < 1:
                        raise AudioDeviceNotFoundError("Selected TX device has no output channels")
                    kwargs["output_device_index"] = device_index
                stream = pa.open(**kwargs)
                while chunk := source.readframes(4096):
                    if stop_event is not None and stop_event.is_set():
                        break
                    stream.write(chunk)
            except AudioDeviceNotFoundError:
                raise
            except Exception as exc:
                raise AudioStreamError(f"Failed to play TX audio: {exc}") from exc
            finally:
                if stream is not None:
                    stream.stop_stream()
                    stream.close()
                pa.terminate()
