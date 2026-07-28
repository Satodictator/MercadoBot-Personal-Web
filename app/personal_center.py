from __future__ import annotations

import logging
from typing import Any

from .config import ROOT, Settings
from .db import Database
from .market_memory import analyze_signal_patterns, calculate_signal_correlations
from .personal_os import build_public_personal_center, load_json, merge_payload
from .private_vault import VaultError, load_vault

logger = logging.getLogger(__name__)


def build_personal_center(settings: Settings, db: Database) -> dict[str, Any]:
    template = load_json(ROOT / "config" / "personal_system_template.json", {})
    template["strategies"] = load_json(ROOT / "config" / "strategy_library.json", [])
    private_payload: dict[str, Any] = {}
    try:
        private_payload, vault_status = load_vault(
            settings.personal_vault_file,
            settings.state_encryption_key,
        )
    except VaultError as exc:
        logger.exception("No se pudo abrir el vault personal")
        vault_status = {"configured": False, "reason": "vault_error", "error": str(exc)}
    payload = merge_payload(template, private_payload) if private_payload else template
    public = build_public_personal_center(
        payload,
        publish_private_summary=settings.publish_private_summary and vault_status.get("configured", False),
        user_timezone=settings.user_timezone,
    )
    history = db.recent_signals(limit=5000)
    public["patterns"] = analyze_signal_patterns(history)
    public["correlations"] = calculate_signal_correlations(history)
    path = settings.personal_vault_file
    public["vault_status"] = {
        **vault_status,
        "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        "private_summary_published": bool(
            settings.publish_private_summary and vault_status.get("configured", False)
        ),
    }
    return public
