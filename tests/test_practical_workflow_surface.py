"""Regression tests for the practical end-to-end workflow surface."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_practical_workflow_is_reachable_from_public_learning_surfaces() -> None:
    mkdocs = _read("mkdocs.yml")
    assert (
        "  - Learn:\n"
        "      - Learning paths: learning-paths.md\n"
        "      - Practical end-to-end workflow: practical-workflow.md"
    ) in mkdocs

    for path in (
        "docs/index.md",
        "docs/getting-started.md",
        "docs/research-workflows.md",
        "docs/for-researchers.md",
        "examples/README.md",
    ):
        assert "practical-workflow.md" in _read(path)


def test_practical_workflow_preserves_demo_and_evidence_boundaries() -> None:
    guide = _read("docs/practical-workflow.md")
    example = _read("examples/end_to_end_research_workflow.py")
    combined = guide + "\n" + example

    assert "synthetic_demo_not_empirical_evidence" in combined
    assert "not empirical validation" in combined
    assert "native-device" in combined
    assert "GP3" in combined
    assert "Evidence status" in guide
    assert "source_unchanged" in example
    assert "assert_frame_equal" in example


def test_guide_routes_real_tracker_data_through_explicit_adapters() -> None:
    guide = _read("docs/practical-workflow.md")

    assert "adapt_gazepoint_samples" in guide
    assert "adapt_processed_table" in guide
    assert "sampling_rate_hz" in guide
    assert "screen_size_px" in guide
    assert "coordinate_scale" in guide


def test_example_composes_reviewable_public_workflow_layers() -> None:
    example = _read("examples/end_to_end_research_workflow.py")

    for public_name in (
        "canonicalize_gaze",
        "ai_flag_anomalies",
        "score_trial_quality",
        "ivt_classify_events",
        "samples_to_event_intervals",
        "map_fixations_to_aois",
        "to_semantic_scanpaths",
        "fingerprint_frame",
        "AuditTrail",
    ):
        assert public_name in example

    for output in (
        "01_source_gaze.csv",
        "02_canonical_gaze.csv",
        "03_qc_samples.csv",
        "04_trial_quality.csv",
        "05_event_samples.csv",
        "06_event_intervals.csv",
        "07_fixation_centroids.csv",
        "08_aoi_definitions.csv",
        "09_fixation_aoi_assignments.csv",
        "10_semantic_scanpaths.csv",
        "provenance.json",
        "workflow_manifest.json",
    ):
        assert output in example
