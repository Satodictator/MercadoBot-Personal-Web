from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    symbol TEXT NOT NULL,
    name TEXT NOT NULL,
    market TEXT NOT NULL,
    price REAL NOT NULL,
    direction TEXT NOT NULL,
    up_probability REAL NOT NULL,
    confidence REAL NOT NULL,
    technical_score REAL NOT NULL,
    news_score REAL NOT NULL,
    model_accuracy REAL,
    data_source TEXT NOT NULL,
    reasons_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_signals_symbol_ts ON signals(symbol, ts DESC);
CREATE TABLE IF NOT EXISTS news_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    symbol TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    sentiment REAL NOT NULL,
    UNIQUE(symbol, url)
);
CREATE INDEX IF NOT EXISTS idx_news_symbol_ts ON news_memory(symbol, ts DESC);
CREATE TABLE IF NOT EXISTS engine_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: Path):
        self.path = path
        self._write_lock = threading.Lock()
        self.initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    def save_signal(self, signal: dict[str, Any]) -> int:
        with self._write_lock, self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO signals (
                    ts, symbol, name, market, price, direction, up_probability,
                    confidence, technical_score, news_score, model_accuracy,
                    data_source, reasons_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal["ts"], signal["symbol"], signal["name"], signal["market"],
                    signal["price"], signal["direction"], signal["up_probability"],
                    signal["confidence"], signal["technical_score"], signal["news_score"],
                    signal.get("model_accuracy"), signal["data_source"],
                    json.dumps(signal.get("reasons", []), ensure_ascii=False),
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def save_news(self, symbol: str, rows: list[dict[str, Any]]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._write_lock, self.connect() as conn:
            conn.executemany(
                """
                INSERT OR IGNORE INTO news_memory(ts, symbol, title, url, sentiment)
                VALUES (?, ?, ?, ?, ?)
                """,
                [(now, symbol, r["title"], r["url"], r["sentiment"]) for r in rows],
            )
            conn.commit()

    def latest_signals(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT s.* FROM signals s
                INNER JOIN (
                    SELECT symbol, MAX(id) AS max_id FROM signals GROUP BY symbol
                ) latest ON s.id = latest.max_id
                ORDER BY confidence DESC, symbol ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._decode_signal(dict(row)) for row in rows]

    def signal_history(self, symbol: str, limit: int = 200) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM signals WHERE symbol = ? ORDER BY id DESC LIMIT ?",
                (symbol, limit),
            ).fetchall()
        return [self._decode_signal(dict(row)) for row in rows]


    def recent_signals(self, limit: int = 2000) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM signals ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._decode_signal(dict(row)) for row in rows]

    def prune(self, keep_signals_per_symbol: int = 500, keep_news_per_symbol: int = 300) -> None:
        """Limita el crecimiento de la memoria persistente sin borrar lo más reciente."""
        with self._write_lock, self.connect() as conn:
            conn.execute(
                """
                DELETE FROM signals WHERE id IN (
                    SELECT id FROM (
                        SELECT id, ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY id DESC) AS rn
                        FROM signals
                    ) ranked WHERE rn > ?
                )
                """,
                (keep_signals_per_symbol,),
            )
            conn.execute(
                """
                DELETE FROM news_memory WHERE id IN (
                    SELECT id FROM (
                        SELECT id, ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY id DESC) AS rn
                        FROM news_memory
                    ) ranked WHERE rn > ?
                )
                """,
                (keep_news_per_symbol,),
            )
            conn.commit()

    def checkpoint(self) -> None:
        with self._write_lock, self.connect() as conn:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.commit()

    def set_state(self, key: str, value: Any) -> None:
        now = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(value, ensure_ascii=False)
        with self._write_lock, self.connect() as conn:
            conn.execute(
                """
                INSERT INTO engine_state(key, value, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
                """,
                (key, payload, now),
            )
            conn.commit()

    def get_state(self, key: str, default: Any = None) -> Any:
        with self.connect() as conn:
            row = conn.execute("SELECT value FROM engine_state WHERE key = ?", (key,)).fetchone()
        return json.loads(row["value"]) if row else default

    @staticmethod
    def _decode_signal(row: dict[str, Any]) -> dict[str, Any]:
        row["reasons"] = json.loads(row.pop("reasons_json", "[]"))
        return row
