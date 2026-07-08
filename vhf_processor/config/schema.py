from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field


class GeneralConfig(BaseModel):
    session_prefix: str = "session"
    data_dir: Path = Path("./data")
    log_level: str = "INFO"
    num_workers: int = 4


class AudioConfig(BaseModel):
    capture_mode: Literal["loopback", "device", "auto"] = "loopback"
    sample_rate: int = 48000
    channels: int = 1
    dtype: str = "int16"
    frame_size: int = 2048
    device_index: int = -1


class VADConfig(BaseModel):
    backend: Literal["silero", "webrtc"] = "silero"
    min_speech_duration_ms: int = 300
    min_silence_duration_ms: int = 1200
    threshold: float = 0.5
    energy_threshold: int = 500
    silero_model_path: str = ""


class GeminiConfig(BaseModel):
    model: str = "gemini-2.5-flash"
    api_key_env: str = "GEMINI_API_KEY"
    project_id: str = ""
    location: str = "us-central1"
    timeout_seconds: int = 30
    max_retries: int = 3

    @property
    def api_key(self) -> str | None:
        return os.environ.get(self.api_key_env) or None


class TranslationConfig(BaseModel):
    enabled: bool = True
    source_language: str = "auto"
    target_language: str = "en"


class LocalStorageConfig(BaseModel):
    audio_dir: Path = Path("./data/audio")
    result_dir: Path = Path("./data/results")


class GCSStorageConfig(BaseModel):
    enabled: bool = True
    bucket_name: str = "vhf-recordings"
    credentials_path: str = ""
    prefix: str = ""


class StorageConfig(BaseModel):
    local: LocalStorageConfig = Field(default_factory=LocalStorageConfig)
    gcs: GCSStorageConfig = Field(default_factory=GCSStorageConfig)
    retention_days: int = 14
    cleanup_interval_hours: int = 24


class AppConfig(BaseModel):
    general: GeneralConfig = Field(default_factory=GeneralConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    vad: VADConfig = Field(default_factory=VADConfig)

    gemini: GeminiConfig = Field(default_factory=GeminiConfig)
    translation: TranslationConfig = Field(default_factory=TranslationConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)

    @classmethod
    def from_toml(cls, path: str | Path) -> AppConfig:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with path.open("rb") as f:
            data = tomllib.load(f)
        return cls.model_validate(data)

    def resolve_paths(self) -> None:
        base = Path(self.general.data_dir).resolve()
        self.general.data_dir = base
        self.storage.local.audio_dir = (base / "audio").resolve()
        self.storage.local.result_dir = (base / "results").resolve()


def load_config(config_path: str | Path = Path("config/default.toml")) -> AppConfig:
    cfg = AppConfig.from_toml(config_path)
    cfg.resolve_paths()
    return cfg
