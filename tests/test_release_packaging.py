from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _project_name_version() -> tuple[str, str]:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    project_match = re.search(r"(?ms)^\[project\]\s*(.*?)(?=^\[|\Z)", pyproject)
    assert project_match is not None
    project = project_match.group(1)
    name_match = re.search(r'(?m)^name\s*=\s*"([^"]+)"\s*$', project)
    version_match = re.search(r'(?m)^version\s*=\s*"([^"]+)"\s*$', project)
    assert name_match is not None
    assert version_match is not None
    return name_match.group(1), version_match.group(1)


def test_first_public_alpha_release_metadata_is_synchronized() -> None:
    name, version = _project_name_version()
    assert name == "gazeforge"
    assert version == "0.1.0a1"

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


def test_release_workflow_builds_exact_tag_and_requires_certified_validation() -> None:
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    required = (
        "Checkout exact release tag",
        "Tag/version mismatch",
        "Require certified release tag and successful package validation",
        "git merge-base --is-ancestor \"$TARGET_SHA\" \"$MAIN_SHA\"",
        "git diff --name-only \"$TARGET_SHA..$MAIN_SHA\"",
        "Post-tag main contains non-orchestration change",
        ".github/workflows/bootstrap-first-release.yml|.github/workflows/release.yml|tests/test_release_packaging.py",
        "for workflow in ci.yml docs.yml; do",
        "full OS/Python matrix",
        "Pages is deliberately not required here",
        "python -m build",
        "python -m twine check dist/*",
        "SHA256SUMS.txt",
        "gh release create",
        "gh workflow run pypi.yml",
    )
    for phrase in required:
        assert phrase in workflow
    assert "for workflow in ci.yml docs.yml pages.yml; do" not in workflow
    assert "Release tag must point at exact current main" not in workflow


def test_pypi_workflow_uses_oidc_and_exact_github_release_assets() -> None:
    workflow = (ROOT / ".github/workflows/pypi.yml").read_text(encoding="utf-8")
    assert "environment: pypi" in workflow
    assert "id-token: write" in workflow
    assert "gh release download" in workflow
    assert "pypa/gh-action-pypi-publish@dc37677b2e1c63e2034f94d8a5b11f265b73ba33" in workflow
    assert "PYPI_API_TOKEN" not in workflow
    assert "password:" not in workflow


def test_first_release_bootstrap_preserves_certified_tag_and_dispatches_current_main() -> None:
    workflow = (ROOT / ".github/workflows/bootstrap-first-release.yml").read_text(
        encoding="utf-8"
    )
    required = (
        'workflows: ["CI", "Docs"]',
        "actions: write",
        "github.event.workflow_run.head_branch == 'main'",
        "github.event.workflow_run.conclusion == 'success'",
        "TARGET_SHA: ${{ github.event.workflow_run.head_sha }}",
        "RELEASE_TAG: v0.1.0a1",
        "Stale workflow_run",
        "for workflow in ci.yml docs.yml; do",
        "git show-ref --verify --quiet",
        "TAG_COMMIT=\"$(git rev-list -n 1 \"$RELEASE_TAG\")\"",
        "git merge-base --is-ancestor \"$TAG_COMMIT\" \"$TARGET_SHA\"",
        "Existing release tag is stale because post-tag main contains non-orchestration change",
        ".github/workflows/bootstrap-first-release.yml|.github/workflows/release.yml|tests/test_release_packaging.py",
        "git tag -a \"$RELEASE_TAG\" \"$TARGET_SHA\"",
        "git push origin \"refs/tags/$RELEASE_TAG\"",
        "gh release view \"$RELEASE_TAG\"",
        "gh run list --workflow release.yml",
        "gh workflow run release.yml --ref main -f tag=\"$RELEASE_TAG\"",
        "certified immutable tag",
    )
    for phrase in required:
        assert phrase in workflow
