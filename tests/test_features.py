import numpy as np
import pandas as pd

from app.features import FEATURE_COLUMNS, add_features


def test_feature_generation():
    n = 500
    idx = pd.date_range("2024-01-01", periods=n, freq="h")
    close = pd.Series(100 + np.linspace(0, 20, n) + np.sin(np.arange(n) / 8), index=idx)
    df = pd.DataFrame({
        "Open": close.shift(1).fillna(close.iloc[0]),
        "High": close + 1,
        "Low": close - 1,
        "Close": close,
        "Volume": 1000 + (np.arange(n) % 30) * 10,
    })
    out = add_features(df).dropna()
    assert len(out) > 300
    assert all(column in out.columns for column in FEATURE_COLUMNS)
    assert np.isfinite(out[FEATURE_COLUMNS].to_numpy()).all()


def test_feature_generation_without_volume():
    n = 500
    idx = pd.date_range("2024-01-01", periods=n, freq="h")
    close = pd.Series(100 + np.sin(np.arange(n) / 10), index=idx)
    df = pd.DataFrame({
        "Open": close, "High": close + 0.5, "Low": close - 0.5,
        "Close": close, "Volume": 0.0,
    })
    out = add_features(df).dropna(subset=FEATURE_COLUMNS)
    assert len(out) > 300
    assert (out["volume_z"] == 0.0).all()
