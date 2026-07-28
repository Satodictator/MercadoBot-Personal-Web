from __future__ import annotations

import logging

import requests

from .config import Settings

logger = logging.getLogger(__name__)


def format_alert(signal: dict[str, object]) -> str:
    arrow = "⬆️" if signal["direction"] == "SUBIDA" else "⬇️"
    return (
        f"{arrow} MercadoBot: {signal['symbol']} — {signal['direction']}\n"
        f"Precio: {signal['price']}\n"
        f"Probabilidad estimada de subida: {float(signal['up_probability']):.1%}\n"
        f"Confianza combinada: {float(signal['confidence']):.1%}\n"
        "Aviso analítico; no es garantía ni orden de inversión."
    )


def send_alert(settings: Settings, signal: dict[str, object]) -> None:
    text = format_alert(signal)
    if settings.telegram_bot_token and settings.telegram_chat_id:
        try:
            requests.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                json={"chat_id": settings.telegram_chat_id, "text": text},
                timeout=12,
            ).raise_for_status()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Falló aviso de Telegram: %s", exc)

    if settings.discord_webhook_url:
        try:
            requests.post(settings.discord_webhook_url, json={"content": text}, timeout=12).raise_for_status()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Falló aviso de Discord: %s", exc)
