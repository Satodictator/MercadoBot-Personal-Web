from __future__ import annotations

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "ret_1", "ret_3", "ret_6", "ret_24", "volatility_24",
    "sma_ratio_10", "sma_ratio_30", "ema_ratio_12", "ema_ratio_26",
    "rsi_14", "macd", "macd_signal", "atr_pct", "bb_position",
    "volume_z", "range_pct", "trend_strength",
]


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    close = out["Close"]
    high = out["High"]
    low = out["Low"]
    volume = out["Volume"].replace(0, np.nan)

    for lag in (1, 3, 6, 24):
        out[f"ret_{lag}"] = close.pct_change(lag)
    out["volatility_24"] = out["ret_1"].rolling(24).std()

    sma10 = close.rolling(10).mean()
    sma30 = close.rolling(30).mean()
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    out["sma_ratio_10"] = close / sma10 - 1
    out["sma_ratio_30"] = close / sma30 - 1
    out["ema_ratio_12"] = close / ema12 - 1
    out["ema_ratio_26"] = close / ema26 - 1

    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.mask((loss == 0) & (gain > 0), 100.0)
    rsi = rsi.mask((gain == 0) & (loss > 0), 0.0)
    rsi = rsi.mask((gain == 0) & (loss == 0), 50.0)
    out["rsi_14"] = rsi

    out["macd"] = (ema12 - ema26) / close
    out["macd_signal"] = out["macd"].ewm(span=9, adjust=False).mean()

    prev_close = close.shift(1)
    true_range = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    atr = true_range.ewm(alpha=1 / 14, adjust=False).mean()
    out["atr_pct"] = atr / close

    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_low = bb_mid - 2 * bb_std
    bb_high = bb_mid + 2 * bb_std
    out["bb_position"] = (close - bb_low) / (bb_high - bb_low).replace(0, np.nan)

    volume_mean = volume.rolling(30).mean()
    volume_std = volume.rolling(30).std()
    out["volume_z"] = ((volume - volume_mean) / volume_std.replace(0, np.nan)).fillna(0.0)
    out["range_pct"] = (high - low) / close
    out["trend_strength"] = (sma10 - sma30) / close

    out = out.replace([np.inf, -np.inf], np.nan)
    return out


def technical_score(row: pd.Series) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []

    if row["sma_ratio_10"] > 0 and row["trend_strength"] > 0:
        score += 0.28
        reasons.append("precio sobre medias y tendencia corta positiva")
    elif row["sma_ratio_10"] < 0 and row["trend_strength"] < 0:
        score -= 0.28
        reasons.append("precio bajo medias y tendencia corta negativa")

    if row["macd"] > row["macd_signal"]:
        score += 0.22
        reasons.append("MACD por encima de su señal")
    else:
        score -= 0.22
        reasons.append("MACD por debajo de su señal")

    rsi = float(row["rsi_14"])
    if 52 <= rsi <= 70:
        score += 0.18
        reasons.append("RSI con impulso alcista no extremo")
    elif 30 <= rsi <= 48:
        score -= 0.18
        reasons.append("RSI con impulso bajista")
    elif rsi > 75:
        score -= 0.08
        reasons.append("RSI en posible sobrecompra")
    elif rsi < 25:
        score += 0.08
        reasons.append("RSI en posible sobreventa")

    if row["ret_6"] > 0:
        score += 0.12
    else:
        score -= 0.12

    if row["volume_z"] > 1.0:
        score += 0.10 if row["ret_1"] > 0 else -0.10
        reasons.append("movimiento acompañado por volumen inusual")

    return float(np.clip(score, -1, 1)), reasons
