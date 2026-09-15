"""Regression tests for software citation and attribution boundaries."""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_citation_page_identifies_immutable_alpha() -> None:
    text = _read("docs/citation-attribution.md")

    assert "0.1.0a1" in text
    assert "10.5281/zenodo.22650013" in text
    assert "0000-0003-2444-9796" in text
    assert "immutable `0.1.0a1` release" in text
    assert "Do not cite `main` as though it were the published alpha" in text


def test_citation_page_requires_commit_identity_for_development_use() -> None:
    text = _read("docs/citation-attribution.md")

    assert "git rev-parse HEAD" in text
    assert "full 40-character Git SHA" in text
    assert "Do not substitute “latest GazeForge”" in text
    assert "Software citation does not establish validation strength" in text


def test_citation_page_preserves_evidence_boundaries() -> None:
    text = _read("docs/citation-attribution.md")

    assert "derived 60 Hz from native 500 Hz data" in text
    assert "not participant-disjoint" in text
    assert "task-agnostic evidence" in text
    assert "bounded partial public-derivative empirical evidence" in text
    assert "Synthetic/demo outputs are examples and tests" in text


def test_citation_page_does_not_invent_software_paper() -> None:
    text = _read("docs/citation-attribution.md")

    assert "There is currently no GazeForge software paper being claimed" in text
    assert "Do not invent a journal citation" in text
    assert "future paper" in text


def test_release_metadata_remains_release_specific() -> None:
    cff = _read("CITATION.cff")
    zenodo = json.loads(_read(".zenodo.json"))

    assert "version: 0.1.0a1" in cff
    assert 'doi: "10.5281/zenodo.22650013"' in cff
    assert zenodo["version"] == "0.1.0a1"
    assert "0.1.0a1" in zenodo["description"]


def test_citation_surface_is_discoverable_from_site_entry_points() -> None:
    mkdocs = _read("mkdocs.yml")
    homepage = _read("docs/index.md")
    release = _read("docs/release-install.md")

    assert "Citation & attribution: citation-attribution.md" in mkdocs
    assert "[Citation & attribution](citation-attribution.md)" in homepage
    assert "[Citation & attribution](citation-attribution.md)" in release
