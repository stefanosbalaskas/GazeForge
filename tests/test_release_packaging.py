from __future__ import annotations

import json
import pathlib
import re
import tomllib


ROOT = pathlib.Path(__file__).resolve().parents[1]


def _project() -> dict[str, object]:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]


def test_first_public_alpha_release_metadata_is_synchronized() -> None:
    project = _project()
    assert project["name"] == "gazeforge"
    assert project["version"] == "0.1.0a1"

    cff = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert re.search(r"(?m)^version:\s*0\.1\.0a1\s*$", cff)
    assert re.search(r"(?m)^date-released:\s*2026-09-07\s*$", cff)
    assert "https://orcid.org/0000-0003-2444-9796" in cff

    zenodo = json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))
    assert zenodo["version"] == "0.1.0a1"
    assert zenodo["upload_type"] == "software"
    assert zenodo["access_right"] == "open"
    assert zenodo["license"] == "mit"
    assert zenodo["creators"][0]["name"] == "Balaskas, Stefanos"
    assert zenodo["creators"][0]["orcid"] == "0000-0003-2444-9796"


def test_release_notes_preserve_alpha_scientific_boundaries() -> None:
    notes = (ROOT / "RELEASE_NOTES_0.1.0a1.md").read_text(encoding="utf-8")
    required = (
        "first public alpha release",
        "not native GP3/60 Hz device validation",
        "does **not** establish exact-byte acquisition",
        "participant-disjoint model validation",
        "stable scientific release remains gated",
    )
    for phrase in required:
        assert phrase in notes


def test_release_workflow_builds_exact_tag_and_requires_exact_main() -> None:
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    required = (
        "Checkout exact release tag",
        "Tag/version mismatch",
        "Release tag must point at exact current main",
        "python -m build",
        "python -m twine check dist/*",
        "SHA256SUMS.txt",
        "gh release create",
        "gh workflow run pypi.yml",
    )
    for phrase in required:
        assert phrase in workflow


def test_pypi_workflow_uses_oidc_and_exact_github_release_assets() -> None:
    workflow = (ROOT / ".github/workflows/pypi.yml").read_text(encoding="utf-8")
    assert "environment: pypi" in workflow
    assert "id-token: write" in workflow
    assert "gh release download" in workflow
    assert "pypa/gh-action-pypi-publish@dc37677b2e1c63e2034f94d8a5b11f265b73ba33" in workflow
    assert "PYPI_API_TOKEN" not in workflow
    assert "password:" not in workflow
