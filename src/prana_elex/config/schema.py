from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class GeneralConfig(BaseModel):
    session_prefix: str = "session"
    data_dir: Path = Path(".")
    log_level: str = "INFO"
    num_workers: int = 4


class AudioConfig(BaseModel):
    capture_mode: Literal["loopback", "device"] = "loopback"
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


class BackendConfig(BaseModel):
    api_url: str = ""
    firebase_api_key: str = ""
    timeout_seconds: float = 150.0


class TranslationConfig(BaseModel):
    enabled: bool = True
    source_language: str = "auto"
    target_language: str = "en"


class LocalStorageConfig(BaseModel):
    audio_dir: Path = Path("./VHF_Storage/audio")
    result_dir: Path = Path("./VHF_Storage/results")


class StorageConfig(BaseModel):
    local: LocalStorageConfig = Field(default_factory=LocalStorageConfig)
    retention_days: int = 14
    cleanup_interval_hours: int = 24


class AppConfig(BaseModel):
    general: GeneralConfig = Field(default_factory=GeneralConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    vad: VADConfig = Field(default_factory=VADConfig)

    backend: BackendConfig = Field(default_factory=BackendConfig)
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

    def resolve_paths(self, base_dir: Path | None = None) -> None:
        base = base_dir.resolve() if base_dir else Path(self.general.data_dir).resolve()
        storage_root = base / "VHF_Storage"
        storage_root.mkdir(parents=True, exist_ok=True)
        self.general.data_dir = storage_root
        self.storage.local.audio_dir = (storage_root / "audio").resolve()
        self.storage.local.result_dir = (storage_root / "results").resolve()

def load_config(config_path: str | Path = Path("config/default.toml"), base_dir: Path | None = None) -> AppConfig:
    cfg = AppConfig.from_toml(config_path)
    cfg.resolve_paths(base_dir)
    return cfg
