from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PRANA_API_", case_sensitive=False)

    environment: str = "development"
    google_cloud_project: str = ""
    google_cloud_location: str = "us-central1"
    firebase_project_id: str = ""
    firebase_web_api_key: str = ""
    google_desktop_oauth_client_id: str = ""
    google_desktop_oauth_client_secret: str = ""
    google_auth_instance_requests_per_minute: int = 60
    google_auth_global_requests_per_minute: int = 300
    storage_bucket: str = ""
    gemini_model: str = "gemini-2.5-flash"
    max_audio_bytes: int = 10 * 1024 * 1024
    max_audio_seconds: int = 120
    signature_clock_skew_seconds: int = 300
    global_daily_audio_seconds: int = 0
    global_monthly_audio_seconds: int = 0
    input_cost_per_million_tokens: float = 0.0
    output_cost_per_million_tokens: float = 0.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
