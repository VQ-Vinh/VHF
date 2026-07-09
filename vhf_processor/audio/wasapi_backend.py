from __future__ import annotations

import threading
from typing import Callable

import numpy as np

from vhf_processor.audio.base import AudioBackend
from vhf_processor.audio.exceptions import AudioDeviceNotFoundError, AudioStreamError
from vhf_processor.config.schema import AudioConfig
from vhf_processor.utils.logger import get_logger

logger = get_logger(__name__)


class WASAPIBackend(AudioBackend):
    _pa = None
    _pa_lock = threading.Lock()

    def __init__(self):
        self._stream = None
        self._running = False

    @property
    def name(self) -> str:
        return "wasapi"

    @classmethod
    def _get_pa(cls):
        if cls._pa is None:
            with cls._pa_lock:
                if cls._pa is None:
                    import pyaudiowpatch as paw
                    cls._pa = paw.PyAudio()
        return cls._pa

    def open_stream(self, config: AudioConfig, callback: Callable[[np.ndarray], None]) -> None:
        import pyaudiowpatch as paw

        pa = self._get_pa()
        mode = config.capture_mode
        device_info = None

        if mode in ("loopback", "auto"):
            device_info = self._find_loopback_device(pa)
            if device_info is None and mode == "loopback":
                raise AudioDeviceNotFoundError(
                    "No WASAPI loopback device found. "
                    "Try capture_mode = 'device' or set a specific device_index."
                )

        if device_info is None:
            device_info = self._resolve_device(config, pa)

        dev_index = device_info["index"]
        dev_name = device_info["name"]
        dev_sr = int(device_info["defaultSampleRate"])

        sr = dev_sr if mode == "loopback" else config.sample_rate
        channels = min(config.channels, device_info["maxInputChannels"])
        if channels < 1:
            channels = device_info["maxInputChannels"]

        frames_per_buffer = config.frame_size

        if config.dtype != "int16":
            logger.warning(f"Only int16 capture supported, got '{config.dtype}'. Falling back to int16.")

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

        def pa_callback(in_data, frame_count, time_info, status):
            try:
                audio = np.frombuffer(in_data, dtype=np.int16).reshape(-1, channels)
                if channels > 1 and config.channels == 1:
                    audio = audio.mean(axis=1)
                if self._running and callback:
                    callback(audio)
            except Exception:
                logger.exception("Audio callback error")
            return (None, paw.paContinue)

        try:
            self._stream = pa.open(
                format=paw.paInt16,
                channels=channels,
                rate=sr,
                input=True,
                input_device_index=dev_index,
                frames_per_buffer=frames_per_buffer,
                stream_callback=pa_callback,
            )
            self._stream.start_stream()
            self._running = True
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

    def _find_loopback_device(self, pa) -> dict | None:
        count = pa.get_device_count()
        for i in range(count):
            try:
                info = pa.get_device_info_by_index(i)
                if info["maxInputChannels"] > 0 and "loopback" in info["name"].lower():
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

    @staticmethod
    def list_devices() -> list[dict]:
        import pyaudiowpatch as paw

        pa = paw.PyAudio()
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
