import json
from pathlib import Path

from app.cloud_export import export_cloud_site
from app.config import get_settings
from app.db import Database


def _signal(idx: int, symbol: str = "TEST") -> dict:
    return {
        "ts": f"2026-07-27T20:{idx:02d}:00+00:00",
        "symbol": symbol,
        "name": symbol,
        "market": "Prueba",
        "price": 100 + idx,
        "direction": "SUBIDA",
        "up_probability": 0.6,
        "confidence": 0.7,
        "technical_score": 0.2,
        "news_score": 0.0,
        "model_accuracy": 0.55,
        "data_source": "Prueba",
        "reasons": ["señal de prueba"],
    }


def test_cloud_export_and_memory_pruning(tmp_path: Path):
    db = Database(tmp_path / "memory.db")
    for idx in range(8):
        db.save_signal(_signal(idx))
    db.prune(keep_signals_per_symbol=3, keep_news_per_symbol=3)
    assert len(db.signal_history("TEST", 20)) == 3

    output = tmp_path / "site"
    status = export_cloud_site(get_settings(), db, output)
    assert status["signals_count"] == 1
    assert (output / "index.html").exists()
    payload = json.loads((output / "data" / "signals.json").read_text(encoding="utf-8"))
    assert payload[0]["symbol"] == "TEST"
