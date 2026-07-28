from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .cloud_export import export_cloud_site
from .config import get_settings
from .db import Database
from .engine import MarketEngine


def main() -> int:
    parser = argparse.ArgumentParser(description="Ejecuta una exploración y genera el sitio estático para GitHub Pages.")
    parser.add_argument("--output", default="site", help="Carpeta de salida del sitio estático")
    args = parser.parse_args()

    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    db = Database(settings.database_file)
    engine = MarketEngine(settings, db)
    results = engine.scan_all()
    db.prune(keep_signals_per_symbol=500, keep_news_per_symbol=300)
    status = export_cloud_site(settings, db, Path(args.output))
    db.checkpoint()

    print(
        f"Exploración terminada: {len(results)} activos correctos; "
        f"{status['signals_count']} señales publicadas."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
