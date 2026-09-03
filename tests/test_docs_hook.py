from types import SimpleNamespace

from scripts.mkdocs_hooks import on_pre_build


def test_mkdocs_hook_generates_conservative_empty_evidence_page(tmp_path):
    (tmp_path / "validation").mkdir()
    (tmp_path / "docs").mkdir()
    config = SimpleNamespace(config_file_path=str(tmp_path / "mkdocs.yml"))

    on_pre_build(config)

    page = (tmp_path / "docs" / "frozen-evidence.md").read_text(encoding="utf-8")
    assert "No integrity-checked frozen empirical benchmark reports" in page
    assert "do **not** become empirical validation" in page
    assert "validation-status.md" in page
