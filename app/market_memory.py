from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Iterable

import numpy as np
import pandas as pd

FEATURES = ["up_probability", "confidence", "technical_score", "news_score", "model_accuracy"]


def _number(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _vector(row: dict[str, Any]) -> np.ndarray:
    return np.array([_number(row.get(name)) for name in FEATURES], dtype=float)


def analyze_signal_patterns(history: Iterable[dict[str, Any]], *, matches_per_symbol: int = 5,
                            minimum_history: int = 8) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in history:
        symbol = str(row.get("symbol") or "")
        if symbol:
            grouped[symbol].append(dict(row))
    output: list[dict[str, Any]] = []
    for symbol, rows in grouped.items():
        rows.sort(key=lambda row: str(row.get("ts") or ""))
        if len(rows) < minimum_history:
            continue
        latest, candidates = rows[-1], []
        latest_vector = _vector(latest)
        for index, row in enumerate(rows[:-1]):
            distance = float(np.linalg.norm(latest_vector - _vector(row)))
            next_row = rows[index + 1]
            price, next_price = _number(row.get("price")), _number(next_row.get("price"))
            next_return = ((next_price / price) - 1) * 100 if price > 0 and next_price > 0 else 0.0
            candidates.append({
                "matched_at": row.get("ts"), "similarity": round(1.0 / (1.0 + distance), 6),
                "next_observed_return_pct": round(next_return, 6), "next_direction": next_row.get("direction"),
                "matched_price": price,
            })
        candidates.sort(key=lambda item: -item["similarity"])
        matches = candidates[:matches_per_symbol]
        denominator = sum(item["similarity"] for item in matches)
        expected = sum(item["similarity"] * item["next_observed_return_pct"] for item in matches) / denominator if denominator else 0.0
        positive = sum(item["next_observed_return_pct"] > 0 for item in matches)
        output.append({
            "symbol": symbol, "name": latest.get("name", symbol), "current_direction": latest.get("direction"),
            "current_confidence": _number(latest.get("confidence")), "expected_next_return_pct": round(expected, 6),
            "positive_case_rate": round(positive / len(matches), 6) if matches else 0.0, "matches": matches,
            "warning": "Comparación sobre señales almacenadas; no garantiza repetición.",
        })
    output.sort(key=lambda item: (-item["current_confidence"], item["symbol"]))
    return output


def calculate_signal_correlations(history: Iterable[dict[str, Any]], *, minimum_overlap: int = 8,
                                  limit: int = 100) -> list[dict[str, Any]]:
    rows = []
    for raw in history:
        try:
            ts = pd.Timestamp(raw.get("ts"))
        except Exception:  # noqa: BLE001
            continue
        symbol, price = str(raw.get("symbol") or ""), _number(raw.get("price"))
        if not symbol or price <= 0:
            continue
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        rows.append({"bucket": ts.floor("h"), "symbol": symbol, "price": price})
    if not rows:
        return []
    frame = pd.DataFrame(rows)
    pivot = frame.pivot_table(index="bucket", columns="symbol", values="price", aggfunc="last")
    returns = pivot.pct_change(fill_method=None)
    symbols, output = list(returns.columns), []
    for index, first in enumerate(symbols):
        for second in symbols[index + 1:]:
            pair = returns[[first, second]].dropna()
            if len(pair) < minimum_overlap:
                continue
            corr = float(pair[first].corr(pair[second]))
            if not math.isfinite(corr):
                continue
            relationship = ("POSITIVA FUERTE" if corr >= 0.7 else "POSITIVA" if corr >= 0.3 else
                            "INVERSA FUERTE" if corr <= -0.7 else "INVERSA" if corr <= -0.3 else "DÉBIL")
            output.append({"asset_a": first, "asset_b": second, "correlation": round(corr, 6),
                           "overlap_points": len(pair), "relationship": relationship,
                           "generated_at": datetime.now(timezone.utc).isoformat()})
    output.sort(key=lambda item: -abs(item["correlation"]))
    return output[:limit]
