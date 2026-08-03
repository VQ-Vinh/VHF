from __future__ import annotations

import queue
import threading
import time
from typing import Callable

import numpy as np

from prana_core.audio.base import AudioBackend
from prana_core.audio.exceptions import AudioDeviceNotFoundError, AudioStreamError
from prana_core.config.schema import AudioConfig
from prana_core.common.logger import get_logger

logger = get_logger(__name__)


class PulseBackend(AudioBackend):
    _QUEUE_CAPACITY = 128
    _pa = None
    _pa_lock = threading.Lock()

    def __init__(self):
        self._stream = None
        self._running = False
        self._sample_rate = 0
        self._audio_queue: queue.Queue[bytes | None] | None = None
        self._capture_worker: threading.Thread | None = None
        self._worker: threading.Thread | None = None
        self._callback: Callable[[np.ndarray], None] | None = None
        self._channels = 1
        self._dropped_frames = 0

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
        self._audio_queue = queue.Queue(maxsize=self._QUEUE_CAPACITY)
        self._callback = callback
        self._channels = channels
        self._dropped_frames = 0

        logger.info(
            "Starting audio capture",
            extra={
                "device": dev_name,
                "sample_rate": sr,
                "channels": channels,
                "frame_size": frames_per_buffer,
            },
        )

        try:
            self._stream = pa.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=sr,
                input=True,
                input_device_index=dev_index,
                frames_per_buffer=frames_per_buffer,
            )
            self._stream.start_stream()
            self._sample_rate = sr
            self._running = True
            self._worker = threading.Thread(
                target=self._process_audio,
                args=(config.channels,),
                name="prana-audio-processing",
                daemon=True,
            )
            self._capture_worker = threading.Thread(
                target=self._capture_audio,
                args=(frames_per_buffer,),
                name="prana-audio-capture",
                daemon=True,
            )
            self._worker.start()
            self._capture_worker.start()
        except Exception as e:
            self._running = False
            self._stop_worker()
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
        self._stop_worker()
        logger.info("Audio capture stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    def _capture_audio(self, frame_count: int) -> None:
        while self._running:
            stream = self._stream
            audio_queue = self._audio_queue
            if stream is None or audio_queue is None:
                return
            try:
                item = stream.read(frame_count, exception_on_overflow=False)
            except Exception:
                if self._running:
                    logger.exception("Audio input read failed")
                return
            try:
                audio_queue.put_nowait(item)
            except queue.Full:
                # Preserve the live edge instead of allowing delayed audio to
                # accumulate when processing is temporarily slower than capture.
                try:
                    audio_queue.get_nowait()
                except queue.Empty:
                    pass
                try:
                    audio_queue.put_nowait(item)
                except queue.Full:
                    pass
                self._dropped_frames += frame_count

    def _process_audio(self, requested_channels: int) -> None:
        reported_drops = 0
        last_drop_log = 0.0
        while True:
            audio_queue = self._audio_queue
            if audio_queue is None:
                return
            item = audio_queue.get()
            if item is None:
                return
            try:
                audio = np.frombuffer(item, dtype=np.int16).reshape(
                    -1, self._channels
                )
                if self._channels > 1 and requested_channels == 1:
                    audio = audio.mean(axis=1)
                callback = self._callback
                if self._running and callback is not None:
                    callback(audio)
            except Exception:
                logger.exception("Audio processing error")
            now = time.monotonic()
            if self._dropped_frames != reported_drops and now - last_drop_log >= 5:
                reported_drops = self._dropped_frames
                last_drop_log = now
                logger.warning(
                    "Audio processing queue dropped %d frames",
                    reported_drops,
                )

    def _stop_worker(self) -> None:
        audio_queue = self._audio_queue
        capture_worker = self._capture_worker
        worker = self._worker
        if (
            capture_worker is not None
            and capture_worker is not threading.current_thread()
        ):
            capture_worker.join(timeout=2)
        if audio_queue is not None:
            try:
                audio_queue.put_nowait(None)
            except queue.Full:
                try:
                    audio_queue.get_nowait()
                except queue.Empty:
                    pass
                try:
                    audio_queue.put_nowait(None)
                except queue.Full:
                    pass
        if worker is not None and worker is not threading.current_thread():
            worker.join(timeout=2)
        self._capture_worker = None
        self._worker = None
        self._audio_queue = None
        self._callback = None

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
