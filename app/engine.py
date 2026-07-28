from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

import numpy as np

from .alerts import send_alert
from .config import Settings, load_watchlist
from .db import Database
from .features import add_features, technical_score
from .market_data import download_history
from .modeling import predict
from .news import fetch_news

logger = logging.getLogger(__name__)


class MarketEngine:
    def __init__(self, settings: Settings, db: Database):
        self.settings = settings
        self.db = db
        self.watchlist = load_watchlist()
        self._scan_lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="market-engine", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _loop(self) -> None:
        while not self._stop.is_set():
            self.scan_all()
            self._stop.wait(self.settings.scan_seconds)

    def scan_all(self) -> list[dict[str, Any]]:
        if not self._scan_lock.acquire(blocking=False):
            return []
        started = datetime.now(timezone.utc)
        results: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        try:
            with ThreadPoolExecutor(max_workers=self.settings.max_workers) as pool:
                futures = {pool.submit(self.analyze_asset, item): item for item in self.watchlist}
                for future in as_completed(futures):
                    item = futures[future]
                    try:
                        results.append(future.result())
                    except Exception as exc:  # noqa: BLE001
                        logger.exception("Error analizando %s", item["symbol"])
                        errors.append({"symbol": item["symbol"], "error": str(exc)})
            self.db.set_state("last_scan", {
                "started_at": started.isoformat(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "ok": len(results),
                "errors": errors,
            })
            return results
        finally:
            self._scan_lock.release()

    def analyze_symbol(self, symbol: str) -> dict[str, Any]:
        item = next((x for x in self.watchlist if x["symbol"].upper() == symbol.upper()), None)
        if item is None:
            item = {"symbol": symbol.upper(), "name": symbol.upper(), "market": "Personalizado"}
        return self.analyze_asset(item)

    def analyze_asset(self, item: dict[str, str]) -> dict[str, Any]:
        symbol = item["symbol"]
        market = download_history(
            symbol,
            self.settings.period,
            self.settings.interval,
            self.settings.min_rows,
        )
        featured = add_features(market.frame).dropna()
        if len(featured) < 160:
            raise ValueError(f"No quedan suficientes filas con indicadores para {symbol}")

        model = predict(symbol, featured, self.settings.model_path, self.settings.model_max_age_hours)
        latest = featured.iloc[-1]
        tech, reasons = technical_score(latest)
        news = fetch_news(item.get("name") or symbol)
        self.db.save_news(symbol, news.items)

        ml_up = model.up_probability
        tech_up = (tech + 1) / 2
        news_up = (news.score + 1) / 2
        combined_up = 0.58 * ml_up + 0.29 * tech_up + 0.13 * news_up

        # La confianza exige acuerdo entre fuentes y un modelo con alguna capacidad fuera de muestra.
        votes = np.array([ml_up, tech_up, news_up], dtype=float)
        agreement = 1.0 - min(float(votes.std()) / 0.5, 1.0)
        edge = abs(combined_up - 0.5) * 2
        accuracy_factor = float(np.clip((model.balanced_accuracy - 0.45) / 0.25, 0.0, 1.0))
        confidence = float(np.clip(0.52 * edge + 0.28 * agreement + 0.20 * accuracy_factor, 0, 1))

        if combined_up >= 0.57:
            direction = "SUBIDA"
        elif combined_up <= 0.43:
            direction = "BAJADA"
        else:
            direction = "NEUTRAL"

        reasons.insert(0, f"modelo ML estima {ml_up:.1%} de subida en la siguiente vela")
        if news.items:
            reasons.append(f"sentimiento agregado de {len(news.items)} titulares: {news.score:+.2f}")
        else:
            reasons.append("sin noticias recientes utilizables; componente de noticias neutral")
        reasons.append(f"exactitud balanceada histórica del modelo: {model.balanced_accuracy:.1%}")

        signal: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "symbol": symbol,
            "name": item.get("name", symbol),
            "market": item.get("market", "Desconocido"),
            "price": round(float(latest["Close"]), 8),
            "direction": direction,
            "up_probability": round(float(combined_up), 6),
            "confidence": round(confidence, 6),
            "technical_score": round(float(tech), 6),
            "news_score": round(float(news.score), 6),
            "model_accuracy": round(float(model.balanced_accuracy), 6),
            "data_source": market.source,
            "interval": market.interval,
            "period": market.period,
            "reasons": reasons,
            "news": news.items[:5],
        }
        self.db.save_signal(signal)
        if direction != "NEUTRAL" and confidence >= self.settings.alert_threshold:
            send_alert(self.settings, signal)
        return signal
