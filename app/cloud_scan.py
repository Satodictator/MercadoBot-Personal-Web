from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .cloud_export import export_cloud_site
from .config import get_settings
from .crypto_markets import CryptoMarketScanner
from .db import Database
from .engine import MarketEngine
from .personal_center import build_personal_center

logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ejecuta una exploración y genera el sitio estático para GitHub Pages."
    )
    parser.add_argument("--output", default="site", help="Carpeta de salida del sitio estático")
    args = parser.parse_args()

    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    db = Database(settings.database_file)
    results = MarketEngine(settings, db).scan_all()

    crypto_result = db.get_state("crypto_market", {})
    crypto_error: dict[str, str] | None = None
    try:
        crypto_result = CryptoMarketScanner(settings).scan()
        db.set_state("crypto_market", crypto_result)
        db.set_state("crypto_last_error", None)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error analizando tokens, pares y arbitraje")
        crypto_error = {"error": str(exc)}
        db.set_state("crypto_last_error", crypto_error)

    # El vault se descifra solo en memoria; sus datos no se escriben en SQLite.
    personal_center = build_personal_center(settings, db)
    db.prune(keep_signals_per_symbol=500, keep_news_per_symbol=300)
    status = export_cloud_site(settings, db, Path(args.output), personal_center=personal_center)
    db.checkpoint()

    print(
        f"Exploración terminada: {len(results)} activos; {status['signals_count']} señales; "
        f"{len(crypto_result.get('token_prices', []))} tokens; "
        f"{len(crypto_result.get('selected_pairs', []))} pares; "
        f"{len(crypto_result.get('arbitrage', []))} arbitrajes; "
        f"vault: {personal_center.get('vault_status', {}).get('reason', 'desconocido')}."
    )
    if crypto_error:
        print("Proveedor cripto temporalmente no disponible; se conservó la última memoria.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
