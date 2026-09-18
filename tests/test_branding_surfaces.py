from __future__ import annotations

import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
BRAND = DOCS / "assets/brand"
PYTHON_SUITE = DOCS / "assets/python-suite-logo.png"


def _png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert data[12:16] == b"IHDR"
    return struct.unpack(">II", data[16:24])


def test_python_suite_logo_is_the_primary_package_identity() -> None:
    assert PYTHON_SUITE.is_file()
    assert _png_dimensions(PYTHON_SUITE) == (256, 229)

    config = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    homepage = (DOCS / "index.md").read_text(encoding="utf-8")

    assert "logo: assets/python-suite-logo.png" in config
    assert "favicon: assets/python-suite-logo.png" in config
    assert "assets/brand/gazeforge-mark.svg" not in config
    assert "assets/brand/gazeforge-favicon.svg" not in config

    assert 'src="docs/assets/python-suite-logo.png"' in readme
    assert "raw.githubusercontent.com/stefanosbalaskas/gpbiometricspy" not in readme
    assert 'src="assets/python-suite-logo.png"' in homepage


def test_legacy_social_preview_remains_upload_ready() -> None:
    preview = BRAND / "gazeforge-social-preview.png"
    assert preview.is_file()
    assert _png_dimensions(preview) == (1280, 640)
    assert preview.stat().st_size < 1_000_000


def test_branding_preserves_accessibility_and_scientific_boundaries() -> None:
    css = (ROOT / "docs/stylesheets/extra.css").read_text(encoding="utf-8")
    guide = (ROOT / "docs/brand-assets.md").read_text(encoding="utf-8").lower()

    assert "prefers-reduced-motion: no-preference" in css
    assert "prefers-reduced-motion: reduce" in css
    assert ".gf-suite-logo" in css
    assert ".gf-hero::before" not in css
    assert "gazeforge-mark.svg" not in css

    assert "official python suite" in guide
    assert "shared package identity" in guide
    assert "native gazepoint gp3 validation" in guide
    assert "presentation layer only" in guide
    assert "not proof of complete wcag conformance" in guide
