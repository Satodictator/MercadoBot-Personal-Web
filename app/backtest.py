from __future__ import annotations

import argparse
import json

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import balanced_accuracy_score, precision_score, recall_score

from .config import get_settings
from .features import FEATURE_COLUMNS, add_features
from .market_data import download_history


def run(symbol: str) -> dict[str, float | int | str]:
    settings = get_settings()
    market = download_history(symbol, "10y", "1d", settings.min_rows)
    data = add_features(market.frame)
    data["forward_return"] = data["Close"].shift(-1) / data["Close"] - 1
    data["target"] = (data["forward_return"] > 0).astype(int)
    data = data.dropna(subset=FEATURE_COLUMNS + ["forward_return", "target"])
    split = int(len(data) * 0.75)
    train, test = data.iloc[:split], data.iloc[split:]
    if len(train) < 200 or len(test) < 50:
        raise ValueError("Historial insuficiente para backtest")

    model = RandomForestClassifier(
        n_estimators=400,
        max_depth=9,
        min_samples_leaf=6,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(train[FEATURE_COLUMNS], train["target"])
    prob = model.predict_proba(test[FEATURE_COLUMNS])[:, 1]
    pred = (prob >= 0.5).astype(int)
    # Estrategia de prueba: largo si probabilidad >= 0,55; fuera del mercado si no.
    position = (prob >= 0.55).astype(float)
    strategy = position * test["forward_return"].to_numpy()
    buy_hold = test["forward_return"].to_numpy()

    return {
        "symbol": symbol,
        "rows_train": int(len(train)),
        "rows_test": int(len(test)),
        "balanced_accuracy": round(float(balanced_accuracy_score(test["target"], pred)), 4),
        "precision_up": round(float(precision_score(test["target"], pred, zero_division=0)), 4),
        "recall_up": round(float(recall_score(test["target"], pred, zero_division=0)), 4),
        "strategy_return": round(float(np.prod(1 + strategy) - 1), 4),
        "buy_hold_return": round(float(np.prod(1 + buy_hold) - 1), 4),
        "exposure": round(float(position.mean()), 4),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest temporal de MercadoBot Personal")
    parser.add_argument("symbols", nargs="+", help="Ejemplo: SPY BTC-USD GC=F")
    args = parser.parse_args()
    results = []
    for symbol in args.symbols:
        try:
            results.append(run(symbol))
        except Exception as exc:  # noqa: BLE001
            results.append({"symbol": symbol, "error": str(exc)})
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
