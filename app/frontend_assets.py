from __future__ import annotations

import base64
import gzip
import hashlib
from dataclasses import dataclass
from pathlib import Path

from .config import ROOT


@dataclass(frozen=True)
class FrontendAsset:
    output_name: str
    parts: tuple[str, ...]
    sha256: str


ASSETS = (
    FrontendAsset(
        output_name="index.html",
        parts=("index.html.gz.b64",),
        sha256="b5e4850a2cd262edb06e7a1fbde2c12e1857ddf41333529d4b1c9e5ca5d3809a",
    ),
    FrontendAsset(
        output_name="app.css",
        parts=("app.css.gz.b64",),
        sha256="567450eeb3866b1e125c05ce05115b3ff71aa1bf73913a00773a94f7716d2a10",
    ),
    FrontendAsset(
        output_name="app.js",
        parts=(
            "app.js.gz.b64",
            "app.js.gz.b64.002",
            "app.js.gz.b64.003",
            "app.js.gz.b64.004",
            "app.js.gz.b64.005",
        ),
        sha256="19df3769c6b6fcf385cd4405ef808fc21552c422d4a89d718ab12b874312f4b1",
    ),
    FrontendAsset(
        output_name="logo.svg",
        parts=("logo.svg.gz.b64",),
        sha256="3d0ab91b1bb80a5c6465df087cde781fe7466169b5061078fa9df6007ea36ad8",
    ),
)


def _decode_asset(bundle_dir: Path, asset: FrontendAsset) -> bytes:
    encoded = "".join(
        (bundle_dir / part).read_text(encoding="ascii").strip()
        for part in asset.parts
    )
    try:
        compressed = base64.b64decode(encoded, validate=True)
        payload = gzip.decompress(compressed)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"No se pudo reconstruir el recurso frontend {asset.output_name}."
        ) from exc
    digest = hashlib.sha256(payload).hexdigest()
    if digest != asset.sha256:
        raise RuntimeError(
            f"SHA-256 incorrecto para {asset.output_name}: {digest}; esperado {asset.sha256}."
        )
    return payload


def materialize_frontend(output_dir: Path, bundle_dir: Path | None = None) -> dict[str, str]:
    source = bundle_dir or (ROOT / "static" / "bundles")
    output_dir.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = {}
    for asset in ASSETS:
        payload = _decode_asset(source, asset)
        target = output_dir / asset.output_name
        target.write_bytes(payload)
        hashes[asset.output_name] = asset.sha256
    return hashes
