from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import ROOT, Settings, load_watchlist
from .db import Database


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def export_cloud_site(settings: Settings, db: Database, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    data_dir = output_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    template = ROOT / "static" / "cloud.html"
    if not template.exists():
        raise FileNotFoundError(f"No existe la plantilla web: {template}")
    shutil.copy2(template, output_dir / "index.html")

    signals = db.latest_signals(limit=500)
    history = db.recent_signals(limit=3000)
    last_scan = db.get_state("last_scan", {})
    now = datetime.now(timezone.utc)
    repository = os.getenv("GITHUB_REPOSITORY_NAME") or os.getenv("GITHUB_REPOSITORY", "")
    repository_url = f"https://github.com/{repository}" if repository else ""

    status: dict[str, Any] = {
        "app": settings.app_name,
        "version": "0.2.0",
        "generated_at": now.isoformat(),
        "last_scan": last_scan,
        "watchlist_count": len(load_watchlist()),
        "signals_count": len(signals),
        "history_count": len(history),
        "interval": settings.interval,
        "period": settings.period,
        "schedule_minutes": int(os.getenv("CLOUD_SCHEDULE_MINUTES", "5")),
        "mode": "GITHUB CLOUD: ANÁLISIS Y ALERTAS; SIN ÓRDENES REALES",
        "repository": repository,
        "repository_url": repository_url,
        "actions_url": f"{repository_url}/actions/workflows/cloud.yml" if repository_url else "",
        "run_url": os.getenv("GITHUB_RUN_URL", ""),
    }

    _write_json(data_dir / "status.json", status)
    _write_json(data_dir / "signals.json", signals)
    _write_json(data_dir / "history.json", history)
    _write_json(data_dir / "watchlist.json", load_watchlist())
    (output_dir / ".nojekyll").write_text("", encoding="utf-8")
    return status
