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

    # Datos spot públicos y selección automática de pares.
    crypto_market_urls: str = (
        "https://data-api.binance.vision,"
        "https://api.binance.com,"
        "https://api.binance.us"
    )
    crypto_request_timeout: float = Field(default=20.0, ge=5.0, le=60.0)
    crypto_quote_assets: str = "USDT,USDC,BTC,ETH"
    crypto_top_pairs: int = Field(default=120, ge=10, le=500)
    crypto_top_tokens: int = Field(default=100, ge=10, le=500)
    crypto_pair_min_volume: float = Field(default=250_000.0, ge=0.0)
    crypto_pair_max_spread_bps: float = Field(default=60.0, ge=1.0, le=500.0)

    # Detector conservador de arbitraje triangular. No ejecuta órdenes.
    arbitrage_start_assets: str = "USDT,USDC"
    arbitrage_fee_bps: float = Field(default=10.0, ge=0.0, le=100.0)
    arbitrage_slippage_bps: float = Field(default=8.0, ge=0.0, le=100.0)
    arbitrage_min_net_bps: float = Field(default=12.0, ge=0.0, le=1000.0)
    arbitrage_min_volume: float = Field(default=1_000_000.0, ge=0.0)
    arbitrage_max_spread_bps: float = Field(default=25.0, ge=1.0, le=500.0)
    arbitrage_min_capacity_usd: float = Field(default=100.0, ge=1.0)
    arbitrage_top_results: int = Field(default=25, ge=1, le=200)

    @property
    def database_file(self) -> Path:
        path = Path(self.database_path)
        return path if path.is_absolute() else ROOT / path

    @property
    def model_path(self) -> Path:
        path = Path(self.model_dir)
        return path if path.is_absolute() else ROOT / path

    @staticmethod
    def _csv_tuple(value: str) -> tuple[str, ...]:
        return tuple(part.strip().upper() for part in value.split(",") if part.strip())

    @property
    def crypto_market_url_list(self) -> tuple[str, ...]:
        return tuple(part.strip() for part in self.crypto_market_urls.split(",") if part.strip())

    @property
    def crypto_quote_asset_list(self) -> tuple[str, ...]:
        return self._csv_tuple(self.crypto_quote_assets)

    @property
    def arbitrage_start_asset_list(self) -> tuple[str, ...]:
        return self._csv_tuple(self.arbitrage_start_assets)


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
