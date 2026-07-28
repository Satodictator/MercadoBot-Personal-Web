from __future__ import annotations

import hashlib

from app.frontend_assets import ASSETS, materialize_frontend


def test_frontend_assets_materialize_with_expected_hashes(tmp_path):
    hashes = materialize_frontend(tmp_path)
    assert hashes == {asset.output_name: asset.sha256 for asset in ASSETS}
    for asset in ASSETS:
        target = tmp_path / asset.output_name
        assert target.exists()
        assert hashlib.sha256(target.read_bytes()).hexdigest() == asset.sha256


def test_frontend_links_and_safety_copy(tmp_path):
    materialize_frontend(tmp_path)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    javascript = (tmp_path / "app.js").read_text(encoding="utf-8")
    css = (tmp_path / "app.css").read_text(encoding="utf-8")

    assert 'href="./app.css"' in html
    assert 'src="./app.js"' in html
    assert "logo.svg" in html
    assert "GitHub Pages" in html
    assert "backend privado" in html.lower() or "backend privado" in javascript.lower()
    assert "mobile-bottom-nav" in html
    assert "sidebar" in html
    assert "right-rail" in html
    assert "localStorage" in javascript
    assert "prefers-reduced-motion" in css
