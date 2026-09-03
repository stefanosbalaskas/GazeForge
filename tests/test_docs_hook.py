from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace


def _load_on_pre_build():
    hook_path = Path(__file__).parents[1] / "scripts" / "mkdocs_hooks.py"
    spec = spec_from_file_location("gazeforge_mkdocs_hooks", hook_path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.on_pre_build


def test_mkdocs_hook_generates_conservative_empty_evidence_page(tmp_path):
    (tmp_path / "validation").mkdir()
    (tmp_path / "docs").mkdir()
    config = SimpleNamespace(config_file_path=str(tmp_path / "mkdocs.yml"))

    _load_on_pre_build()(config)

    page = (tmp_path / "docs" / "frozen-evidence.md").read_text(encoding="utf-8")
    assert "No integrity-checked frozen empirical benchmark reports" in page
    assert "do **not** become empirical validation" in page
    assert "validation-status.md" in page
