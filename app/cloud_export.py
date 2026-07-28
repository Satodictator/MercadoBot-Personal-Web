from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .config import Settings, load_watchlist
from .db import Database
from .frontend_assets import materialize_frontend


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def _write_csv(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    items = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not items:
        path.write_text("", encoding="utf-8")
        return
    columns: list[str] = []
    for row in items:
        for key in row:
            if key not in columns:
                columns.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in items:
            writer.writerow({
                key: json.dumps(value, ensure_ascii=False)
                if isinstance(value, (dict, list))
                else value
                for key, value in row.items()
            })


def _build_opportunities(
    signals: list[dict[str, Any]],
    arbitrage: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for signal in signals:
        confidence = float(signal.get("confidence") or 0)
        if signal.get("direction") == "NEUTRAL" or confidence < 0.60:
            continue
        output.append({
            "type": "MARKET_SIGNAL",
            "category": "GROWTH" if signal.get("direction") == "SUBIDA" else "MARKET",
            "priority_score": round(confidence * 100, 2),
            "asset": signal.get("symbol"),
            "market": signal.get("market", ""),
            "title": f"{signal.get('direction')} probable en {signal.get('symbol')}",
            "strategy": "Momentum / tendencia / confirmación",
            "current_price": signal.get("price"),
            "capital_required": None,
            "duration": signal.get("interval", ""),
            "key_time": None,
            "countdown_seconds": None,
            "net_edge_pct": None,
            "status": "VERIFICAR",
            "details": signal.get("reasons", []),
            "generated_at": signal.get("ts"),
        })
    for row in arbitrage:
        output.append({
            "type": "TRIANGULAR_ARBITRAGE",
            "category": "ARBITRAGE",
            "priority_score": round(float(row.get("net_edge_bps") or 0), 2),
            "asset": " → ".join(row.get("route", [])),
            "market": row.get("source", "Spot"),
            "title": "Arbitraje triangular para verificar",
            "strategy": "Arbitraje",
            "current_price": None,
            "capital_required": row.get("sample_notional"),
            "duration": "Muy corto; GitHub no es baja latencia",
            "key_time": None,
            "countdown_seconds": None,
            "net_edge_pct": row.get("net_edge_pct"),
            "status": row.get("status", "VERIFICAR"),
            "details": row.get("legs", []),
            "generated_at": row.get("generated_at"),
        })
    output.sort(key=lambda item: -float(item.get("priority_score") or 0))
    return output[:200]


def export_cloud_site(
    settings: Settings,
    db: Database,
    output_dir: Path,
    *,
    personal_center: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    data_dir, reports_dir = output_dir / "data", output_dir / "reports"
    data_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    frontend_hashes = materialize_frontend(output_dir)

    signals = db.latest_signals(limit=500)
    history = db.recent_signals(limit=5000)
    last_scan = db.get_state("last_scan", {})
    crypto = db.get_state("crypto_market", {}) or {}
    token_prices = crypto.get("token_prices", [])
    selected_pairs = crypto.get("selected_pairs", [])
    arbitrage = crypto.get("arbitrage", [])
    personal = personal_center or {}
    opportunities = _build_opportunities(signals, arbitrage)
    repository = os.getenv("GITHUB_REPOSITORY_NAME") or os.getenv(
        "GITHUB_REPOSITORY", ""
    )
    repository_url = f"https://github.com/{repository}" if repository else ""
    vault_status = personal.get("vault_status", {})
    status: dict[str, Any] = {
        "app": settings.app_name,
        "version": "0.5.0",
        "interface": "PRO_FINANCIAL_DASHBOARD",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "last_scan": last_scan,
        "watchlist_count": len(load_watchlist()),
        "signals_count": len(signals),
        "history_count": len(history),
        "token_count": len(token_prices),
        "pair_count": len(selected_pairs),
        "arbitrage_count": len(arbitrage),
        "opportunity_count": len(opportunities),
        "pattern_count": len(personal.get("patterns", [])),
        "correlation_count": len(personal.get("correlations", [])),
        "feature_count": len(personal.get("features", [])),
        "crypto_pairs_seen": crypto.get("pairs_seen", 0),
        "crypto_generated_at": crypto.get("generated_at"),
        "crypto_source": crypto.get("source", ""),
        "crypto_mode": crypto.get("mode", ""),
        "crypto_error": db.get_state("crypto_last_error", None),
        "arbitrage_assumptions": crypto.get("assumptions", {}),
        "vault_configured": bool(vault_status.get("configured")),
        "vault_reason": vault_status.get("reason", "unknown"),
        "private_summary_published": bool(
            vault_status.get("private_summary_published", False)
        ),
        "personal_dashboard": personal.get("dashboard", {}),
        "interval": settings.interval,
        "period": settings.period,
        "schedule_minutes": int(os.getenv("CLOUD_SCHEDULE_MINUTES", "5")),
        "mode": (
            "GITHUB CLOUD: INTERFAZ PROFESIONAL, ANÁLISIS, MEMORIA CIFRADA "
            "Y PLANIFICACIÓN; SIN ÓRDENES REALES"
        ),
        "repository": repository,
        "repository_url": repository_url,
        "actions_url": (
            f"{repository_url}/actions/workflows/cloud.yml"
            if repository_url
            else ""
        ),
        "run_url": os.getenv("GITHUB_RUN_URL", ""),
        "frontend_hashes": frontend_hashes,
        "authentication": {
            "available": False,
            "status": "REQUIRES_PRIVATE_BACKEND",
            "detail": (
                "GitHub Pages es público y estático; una sesión segura real requiere "
                "backend privado autenticado."
            ),
        },
    }

    payloads = {
        "status": status,
        "signals": signals,
        "history": history,
        "watchlist": load_watchlist(),
        "tokens": token_prices,
        "pairs": selected_pairs,
        "arbitrage": arbitrage,
        "opportunities": opportunities,
        "personal": {
            key: value
            for key, value in personal.items()
            if key not in {"patterns", "correlations"}
        },
        "patterns": personal.get("patterns", []),
        "correlations": personal.get("correlations", []),
        "sessions": personal.get("sessions", []),
        "features": personal.get("features", []),
        "strategies": personal.get("strategy_catalog", []),
        "goals": personal.get("goals", []),
        "capital": personal.get("capital_lots", []),
        "countdowns": personal.get("countdowns", []),
        "calendar": personal.get("calendar_events", []),
        "journal": personal.get("journal", []),
        "positions": personal.get("open_positions", []),
    }
    for name, payload in payloads.items():
        _write_json(data_dir / f"{name}.json", payload)
    for name, rows in {
        "signals": signals,
        "tokens": token_prices,
        "pairs": selected_pairs,
        "arbitrage": arbitrage,
        "opportunities": opportunities,
        "journal": personal.get("journal", []),
        "closed_trades": personal.get("closed_trades", []),
    }.items():
        _write_csv(reports_dir / f"{name}.csv", rows)
    (output_dir / ".nojekyll").write_text("", encoding="utf-8")
    return status
