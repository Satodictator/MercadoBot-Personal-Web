from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "MercadoBot Personal"
    host: str = "127.0.0.1"
    port: int = 8000
    scan_seconds: int = Field(default=300, ge=60)
    interval: str = "1h"
    period: str = "730d"
    min_rows: int = Field(default=350, ge=150)
    alert_threshold: float = Field(default=0.68, ge=0.5, le=0.95)
    max_workers: int = Field(default=4, ge=1, le=16)
    model_max_age_hours: int = Field(default=6, ge=1, le=168)
    database_path: str = "data/mercadobot.db"
    model_dir: str = "models"
    log_level: str = "INFO"

    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_data_feed: str = "iex"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    discord_webhook_url: str = ""

    @property
    def database_file(self) -> Path:
        path = Path(self.database_path)
        return path if path.is_absolute() else ROOT / path

    @property
    def model_path(self) -> Path:
        path = Path(self.model_dir)
        return path if path.is_absolute() else ROOT / path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.database_file.parent.mkdir(parents=True, exist_ok=True)
    settings.model_path.mkdir(parents=True, exist_ok=True)
    return settings


def load_watchlist() -> list[dict[str, Any]]:
    path = ROOT / "config" / "watchlist.json"
    with path.open("r", encoding="utf-8") as handle:
        rows = json.load(handle)
    if not isinstance(rows, list):
        raise ValueError("config/watchlist.json debe contener una lista")
    return rows
