from __future__ import annotations

import struct
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "docs/assets/brand"


def _png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert data[12:16] == b"IHDR"
    return struct.unpack(">II", data[16:24])


def test_brand_assets_exist_and_are_parseable() -> None:
    informative = (
        BRAND / "gazeforge-mark.svg",
        BRAND / "gazeforge-lockup.svg",
        BRAND / "gazeforge-social-preview.svg",
    )
    for path in informative:
        assert path.is_file()
        root = ET.parse(path).getroot()
        ns = {"svg": "http://www.w3.org/2000/svg"}
        assert root.find("svg:title", ns) is not None
        assert root.find("svg:desc", ns) is not None

    favicon = BRAND / "gazeforge-favicon.svg"
    assert favicon.is_file()
    ET.parse(favicon)


def test_mkdocs_brand_paths_resolve() -> None:
    config = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    assert "logo: assets/brand/gazeforge-mark.svg" in config
    assert "favicon: assets/brand/gazeforge-favicon.svg" in config
    assert "Brand & sharing: brand-assets.md" in config

    assert (ROOT / "docs/brand-assets.md").is_file()


def test_social_preview_is_upload_ready() -> None:
    preview = BRAND / "gazeforge-social-preview.png"
    assert preview.is_file()
    assert _png_dimensions(preview) == (1280, 640)
    assert preview.stat().st_size < 1_000_000


def test_branding_preserves_accessibility_and_scientific_boundaries() -> None:
    css = (ROOT / "docs/stylesheets/extra.css").read_text(encoding="utf-8")
    guide = (ROOT / "docs/brand-assets.md").read_text(encoding="utf-8").lower()

    assert "prefers-reduced-motion: no-preference" in css
    assert "prefers-reduced-motion: reduce" in css
    assert ".gf-hero::before" in css
    assert "native gazepoint gp3 validation" in guide
    assert "presentation layer only" in guide
    assert "surveillance" in guide
    assert "diagnosis" in guide
