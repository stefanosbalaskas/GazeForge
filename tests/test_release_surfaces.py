"""Tests for public release/documentation boundary semantics."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_release_page_separates_published_alpha_from_current_main() -> None:
    text = (PROJECT_ROOT / "docs" / "release-install.md").read_text(encoding="utf-8")

    assert 'python -m pip install "gazeforge==0.1.0a1"' in text
    assert 'python -m pip install -e ".[plot]"' in text
    assert "does **not** mean `gazeforge[plot]==0.1.0a1`" in text
    assert "immutable published alpha" in text
    assert "current repository development tree" in text


def test_release_page_carries_frozen_distribution_hashes() -> None:
    text = (PROJECT_ROOT / "docs" / "release-install.md").read_text(encoding="utf-8")

    assert "3e409fbfc3c194db30ba25fefdf7f6459a3a003aefa0ab4303555d96982fbb46" in text
    assert "cee4e061a90d74b3a354a0fb4aa5c7bd00d53577e17167f75342cd476a5c25fa" in text
    assert "10.5281/zenodo.22650013" in text


def test_root_changelog_retains_unreleased_boundary() -> None:
    changelog = (PROJECT_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## Unreleased" in changelog

    seed = (PROJECT_ROOT / "docs" / "changelog.md").read_text(encoding="utf-8")
    assert "Unreleased" in seed
    assert "not part of the immutable `0.1.0a1`" in seed
