from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


@dataclass
class MarketFrame:
    frame: pd.DataFrame
    source: str
    interval: str
    period: str


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns={c: c.title() for c in df.columns})
    required_price = ["Open", "High", "Low", "Close"]
    missing = [c for c in required_price if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas de mercado: {missing}")
    if "Volume" not in df.columns:
        df["Volume"] = 0.0
    required = required_price + ["Volume"]
    df = df[required].copy()
    for col in required:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    if df.index.tz is not None:
        df.index = df.index.tz_convert("UTC").tz_localize(None)
    return df[~df.index.duplicated(keep="last")].sort_index()


def download_history(symbol: str, period: str, interval: str, min_rows: int) -> MarketFrame:
    attempts = [
        (period, interval),
        ("2y", "1d"),
        ("10y", "1d"),
    ]
    last_error: Exception | None = None
    for candidate_period, candidate_interval in attempts:
        try:
            df = yf.download(
                symbol,
                period=candidate_period,
                interval=candidate_interval,
                auto_adjust=True,
                progress=False,
                threads=False,
                timeout=25,
            )
            df = _normalize(df)
            if len(df) >= min_rows:
                return MarketFrame(df, "Yahoo Finance", candidate_interval, candidate_period)
            last_error = ValueError(f"Solo se recibieron {len(df)} filas para {symbol}")
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning("Falló descarga %s %s/%s: %s", symbol, candidate_period, candidate_interval, exc)
    raise RuntimeError(f"No se pudo obtener historial suficiente para {symbol}: {last_error}")
