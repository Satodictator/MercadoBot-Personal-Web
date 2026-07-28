from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

from .config import ROOT, get_settings, load_watchlist
from .db import Database
from .engine import MarketEngine

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
db = Database(settings.database_file)
engine = MarketEngine(settings, db)


@asynccontextmanager
async def lifespan(_: FastAPI):
    engine.start()
    yield
    engine.stop()


app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    description="Analizador personal multiactivo con memoria, patrones, noticias y alertas.",
    lifespan=lifespan,
)


@app.get("/")
def dashboard() -> FileResponse:
    return FileResponse(Path(ROOT) / "static" / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/status")
def status() -> dict[str, object]:
    return {
        "app": settings.app_name,
        "version": "0.2.0",
        "scan_seconds": settings.scan_seconds,
        "interval": settings.interval,
        "watchlist_count": len(engine.watchlist),
        "last_scan": db.get_state("last_scan", {}),
        "mode": "ANÁLISIS Y ALERTAS; SIN ÓRDENES REALES",
    }


@app.get("/api/watchlist")
def watchlist() -> list[dict[str, object]]:
    return load_watchlist()


@app.get("/api/signals")
def signals(limit: int = Query(default=100, ge=1, le=500)) -> list[dict[str, object]]:
    return db.latest_signals(limit)


@app.get("/api/history/{symbol}")
def history(symbol: str, limit: int = Query(default=200, ge=1, le=2000)) -> list[dict[str, object]]:
    return db.signal_history(symbol.upper(), limit)


@app.post("/api/scan")
def scan() -> dict[str, object]:
    rows = engine.scan_all()
    return {"completed": len(rows), "signals": rows}


@app.post("/api/analyze/{symbol}")
def analyze(symbol: str) -> dict[str, object]:
    try:
        return engine.analyze_symbol(symbol)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
