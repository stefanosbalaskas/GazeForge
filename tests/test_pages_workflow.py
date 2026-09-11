from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_pages_redeploys_for_any_package_source_change() -> None:
    workflow = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")

    assert '- "src/gazeforge/**"' in workflow
    assert '- "src/gazeforge/dashboard.py"' not in workflow
    assert '- "src/gazeforge/evidence_details.py"' not in workflow
    assert "mkdocs build --strict --site-dir site" in workflow
