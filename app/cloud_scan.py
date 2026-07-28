from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .cloud_export import export_cloud_site
from .config import get_settings
from .crypto_markets import CryptoMarketScanner
from .db import Database
from .engine import MarketEngine

logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ejecuta una exploración y genera el sitio estático para GitHub Pages."
    )
    parser.add_argument(
        "--output",
        default="site",
        help="Carpeta de salida del sitio estático",
    )
    args = parser.parse_args()

    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    db = Database(settings.database_file)
    engine = MarketEngine(settings, db)
    results = engine.scan_all()

    crypto_result = db.get_state("crypto_market", {})
    crypto_error: dict[str, str] | None = None
    try:
        crypto_result = CryptoMarketScanner(settings).scan()
        db.set_state("crypto_market", crypto_result)
        db.set_state("crypto_last_error", None)
    except Exception as exc:  # noqa: BLE001 - retain prior memory on provider failures
        logger.exception("Error analizando tokens, pares y arbitraje")
        crypto_error = {"error": str(exc)}
        db.set_state("crypto_last_error", crypto_error)

    db.prune(keep_signals_per_symbol=500, keep_news_per_symbol=300)
    status = export_cloud_site(settings, db, Path(args.output))
    db.checkpoint()

    print(
        f"Exploración terminada: {len(results)} activos correctos; "
        f"{status['signals_count']} señales; "
        f"{len(crypto_result.get('token_prices', []))} tokens; "
        f"{len(crypto_result.get('selected_pairs', []))} pares; "
        f"{len(crypto_result.get('arbitrage', []))} arbitrajes candidatos."
    )
    if crypto_error:
        print(
            "El proveedor cripto falló temporalmente; se publicó la última memoria disponible: "
            f"{crypto_error['error']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
