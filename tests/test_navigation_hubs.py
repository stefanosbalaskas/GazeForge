"""Regression tests for the validation and benchmark navigation hubs."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_hubs_are_first_entries_in_navigation_sections() -> None:
    mkdocs = _read("mkdocs.yml")

    assert (
        "  - Validation:\n"
        "      - Guide: validation-evidence-guide.md\n"
        "      - Evidence status: evidence-status.md"
    ) in mkdocs
    assert (
        "  - Benchmarks:\n"
        "      - Guide: benchmark-guide.md\n"
        "      - Lund2013:"
    ) in mkdocs


def test_detailed_benchmark_routes_remain_available() -> None:
    mkdocs = _read("mkdocs.yml")

    for route in (
        "lund2013-benchmark.md",
        "hollywood2-benchmark.md",
        "gaze-in-wild-benchmark.md",
        "visus-public-partial-evidence.md",
        "frozen-evidence.md",
        "source-resolution-status.md",
        "validation-scope-certificates.md",
    ):
        assert route in mkdocs


def test_navigation_hubs_preserve_scientific_boundaries() -> None:
    validation = _read("docs/validation-evidence-guide.md")
    benchmarks = _read("docs/benchmark-guide.md")
    combined = validation + "\n" + benchmarks

    assert "Evidence status" in combined
    assert "canonical public status layer" in validation
    assert "derived 60 Hz" in combined
    assert "native 60 Hz" in combined
    assert "GP3" in combined
    assert "source-token" in combined
    assert "not a participant" in combined
    assert "participant-disjoint" in combined
    assert "task-agnostic" in combined
    assert "TrIdx" in combined
    assert "bounded" in combined.lower()
    assert "public derivative" in combined.lower()
    assert "league table" in benchmarks.lower()


def test_hubs_are_linked_from_public_entry_surfaces() -> None:
    homepage = _read("docs/index.md")
    researchers = _read("docs/for-researchers.md")

    for target in ("validation-evidence-guide.md", "benchmark-guide.md"):
        assert target in homepage
        assert target in researchers
