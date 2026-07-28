from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import balanced_accuracy_score

from .features import FEATURE_COLUMNS


@dataclass
class ModelPrediction:
    up_probability: float
    balanced_accuracy: float
    trained_rows: int
    retrained: bool


def _slug(symbol: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", symbol)


def _paths(model_dir: Path, symbol: str) -> tuple[Path, Path]:
    stem = _slug(symbol)
    return model_dir / f"{stem}.joblib", model_dir / f"{stem}.json"


def _dataset(featured: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    data = featured.copy()
    # Objetivo: dirección de la siguiente vela. Se eliminan zonas casi planas para reducir ruido.
    forward = data["Close"].shift(-1) / data["Close"] - 1
    threshold = data["ret_1"].rolling(100).std().median() * 0.08
    threshold = float(threshold) if pd.notna(threshold) else 0.0
    data["target"] = (forward > max(threshold, 0.0)).astype(int)
    data = data.dropna(subset=FEATURE_COLUMNS + ["target"])
    return data[FEATURE_COLUMNS], data["target"].astype(int)


def _train(X: pd.DataFrame, y: pd.Series) -> tuple[RandomForestClassifier, float]:
    split = max(int(len(X) * 0.8), len(X) - 200)
    split = min(max(split, 100), len(X) - 30)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]

    model = RandomForestClassifier(
        n_estimators=320,
        max_depth=9,
        min_samples_leaf=5,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    if y_test.nunique() > 1:
        pred = model.predict(X_test)
        accuracy = float(balanced_accuracy_score(y_test, pred))
    else:
        accuracy = 0.5
    model.fit(X, y)
    return model, accuracy


def predict(
    symbol: str,
    featured: pd.DataFrame,
    model_dir: Path,
    max_age_hours: int,
) -> ModelPrediction:
    X, y = _dataset(featured)
    if len(X) < 180 or y.nunique() < 2:
        raise ValueError(f"Datos insuficientes para entrenar {symbol}: {len(X)} filas")

    model_file, meta_file = _paths(model_dir, symbol)
    model = None
    meta: dict[str, object] = {}
    retrained = True
    if model_file.exists() and meta_file.exists():
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            trained_at = datetime.fromisoformat(str(meta["trained_at"]))
            if datetime.now(timezone.utc) - trained_at <= timedelta(hours=max_age_hours):
                model = joblib.load(model_file)
                retrained = False
        except Exception:  # noqa: BLE001
            model = None

    if model is None:
        model, accuracy = _train(X.iloc[:-1], y.iloc[:-1])
        meta = {
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "balanced_accuracy": accuracy,
            "trained_rows": int(len(X) - 1),
            "features": FEATURE_COLUMNS,
        }
        joblib.dump(model, model_file)
        meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    else:
        accuracy = float(meta.get("balanced_accuracy", 0.5))

    latest = featured.dropna(subset=FEATURE_COLUMNS).iloc[-1:][FEATURE_COLUMNS]
    probs = model.predict_proba(latest)[0]
    class_map = {int(cls): float(prob) for cls, prob in zip(model.classes_, probs, strict=True)}
    up_probability = class_map.get(1, 0.5)
    # Penaliza modelos sin evidencia fuera de muestra.
    reliability = float(np.clip((accuracy - 0.5) / 0.15, 0.0, 1.0))
    up_probability = 0.5 + (up_probability - 0.5) * (0.45 + 0.55 * reliability)
    return ModelPrediction(
        up_probability=float(np.clip(up_probability, 0.02, 0.98)),
        balanced_accuracy=accuracy,
        trained_rows=int(meta.get("trained_rows", len(X) - 1)),
        retrained=retrained,
    )
