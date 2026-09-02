import pandas as pd
import pytest

from gazeforge import DynamicAOIKeyframe
from gazeforge.dynamic_evaluation import (
    dynamic_aoi_snapshot,
    dynamic_fixation_assignment_agreement,
    evaluate_dynamic_aoi_tracks,
)


def _track(aoi_id="a", label="target", xshift=0.0):
    return [
        DynamicAOIKeyframe(aoi_id, label, 0, xshift, 0, 100 + xshift, 100),
        DynamicAOIKeyframe(aoi_id, label, 100, 20 + xshift, 0, 120 + xshift, 100),
    ]


def test_dynamic_snapshot_interpolates_without_extrapolation():
    track = _track()
    middle = dynamic_aoi_snapshot(track, 50, max_interpolation_gap_ms=100)
    assert len(middle) == 1
    assert middle[0].xmin == pytest.approx(10)
    assert dynamic_aoi_snapshot(track, 150, max_interpolation_gap_ms=100) == []


def test_identical_dynamic_tracks_have_perfect_geometry_agreement():
    result = evaluate_dynamic_aoi_tracks(
        _track(),
        _track(),
        timestamps_ms=[0, 50, 100],
        max_interpolation_gap_ms=100,
    )
    assert result.summary["precision"] == pytest.approx(1.0)
    assert result.summary["recall"] == pytest.approx(1.0)
    assert result.summary["f1"] == pytest.approx(1.0)
    assert result.summary["mean_matched_iou"] == pytest.approx(1.0)
    assert len(result.matches) == 3


def test_dynamic_tracks_use_global_tp_fp_fn_over_timestamp_grid():
    result = evaluate_dynamic_aoi_tracks(
        _track(xshift=10),
        _track(),
        timestamps_ms=[0, 50, 100, 150],
        max_interpolation_gap_ms=100,
        min_iou=0.5,
    )
    assert result.summary["true_positive"] == 3
    assert result.summary["false_positive"] == 0
    assert result.summary["false_negative"] == 0
    assert result.summary["n_empty_timestamps"] == 1
    assert 0.8 < result.summary["mean_matched_iou"] < 1.0


def test_dynamic_label_requirement_turns_semantic_mismatch_into_errors():
    result = evaluate_dynamic_aoi_tracks(
        _track(label="model"),
        _track(label="human"),
        timestamps_ms=[0, 50, 100],
        require_label_match=True,
    )
    assert result.summary["true_positive"] == 0
    assert result.summary["false_positive"] == 3
    assert result.summary["false_negative"] == 3


def test_dynamic_fixation_assignment_agreement_uses_same_geometry():
    fixations = pd.DataFrame(
        {
            "timestamp_ms": [0.0, 50.0, 100.0, 150.0],
            "x_px": [20.0, 30.0, 40.0, 40.0],
            "y_px": [20.0, 20.0, 20.0, 20.0],
        }
    )
    metrics = dynamic_fixation_assignment_agreement(
        fixations,
        _track(),
        _track(),
        max_interpolation_gap_ms=100,
    )
    assert metrics["n_aligned_fixations"] == 4
    assert metrics["exact_agreement"] == pytest.approx(1.0)
    assert metrics["cohen_kappa"] == pytest.approx(1.0)


def test_dynamic_aoi_benchmark_report_retains_evidence_and_fingerprint():
    from gazeforge import BenchmarkDatasetCard
    from gazeforge.dynamic_evaluation import build_dynamic_aoi_benchmark_report

    evaluation = evaluate_dynamic_aoi_tracks(
        _track(),
        _track(),
        timestamps_ms=[0, 50, 100],
    )
    card = BenchmarkDatasetCard(
        name="human-aoi",
        version="1",
        source="test",
        license="test",
        task="dynamic AOI",
        sampling_rates_hz=[60.0],
        annotation_origin="human-manual",
        sampling_origin="native",
        reference_strength="human-reference",
        human_annotator_count=2,
    )
    report = build_dynamic_aoi_benchmark_report(
        evaluation,
        benchmark=card,
        model={"name": "test-model"},
    )
    assert report["benchmark"]["sampling_origin"] == "native"
    assert report["benchmark"]["reference_strength"] == "human-reference"
    assert report["protocol"]["timestamp_grid_explicit"] is True
    assert len(report["report_fingerprint_sha256"]) == 64


def test_dynamic_evaluation_accepts_numpy_timestamp_grid():
    import numpy as np

    result = evaluate_dynamic_aoi_tracks(
        _track(),
        _track(),
        timestamps_ms=np.array([0.0, 50.0, 100.0]),
    )
    assert result.summary["n_timestamps"] == 3


def test_dynamic_evaluation_requires_strictly_increasing_grid():
    with pytest.raises(ValueError, match="strictly increasing"):
        evaluate_dynamic_aoi_tracks(
            _track(),
            _track(),
            timestamps_ms=[100.0, 0.0, 50.0],
        )
