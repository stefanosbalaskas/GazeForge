"""Tests for public release/documentation boundary semantics."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_release_page_separates_published_alpha_from_current_main() -> None:
    text = (PROJECT_ROOT / "docs" / "release-install.md").read_text(encoding="utf-8")

    assert 'python -m pip install "gazeforge==0.1.0a2"' in text
    assert 'python -m pip install "gazeforge[plot]==0.1.0a2"' in text
    assert "immutable published alpha" in text
    assert "current repository development tree" in text
    assert "v0.1.0a2" in text


def test_release_page_carries_frozen_distribution_hashes() -> None:
    text = (PROJECT_ROOT / "docs" / "release-install.md").read_text(encoding="utf-8")

    assert "ff8bee1efacac7b36cccae6ecfed56dfd428d6c85e3b37263673321c1b6e8705" in text
    assert "36f70467422ffd1879500c77415fbb38a95ae481f9f66f305b918ed0b7f425c7" in text
    assert "cc2b74eb5f56bf7a1ab4c7db00c0f68eba5ee436" in text
    assert "10.5281/zenodo.22650012" in text
    assert "10.5281/zenodo.22650013" in text


def test_root_changelog_retains_unreleased_boundary() -> None:
    changelog = (PROJECT_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## Unreleased" in changelog

    seed = (PROJECT_ROOT / "docs" / "changelog.md").read_text(encoding="utf-8")
    assert "Unreleased" in seed
    assert "not part of the immutable `0.1.0a2`" in seed


def test_public_entry_points_do_not_reintroduce_stale_evidence_claims() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    homepage = (PROJECT_ROOT / "docs" / "index.md").read_text(encoding="utf-8")

    for text in (readme, homepage):
        assert "infrastructure validated, empirical execution pending" not in text
        assert "frozen exact-distribution participant-disjoint evidence available" not in text
        assert "Reviewed empirical evidence" in text
        assert "Bounded empirical evidence" in text

    assert "3 reviewed datasets" not in homepage
    assert "Generated &amp; fail-closed" in homepage
    assert "evidence-status.md" in readme
    assert "evidence-status.md" in homepage
