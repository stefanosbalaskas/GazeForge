import json

import pandas as pd
import pytest

from gazeforge import (
    AOI,
    BenchmarkDatasetCard,
    aoi_boundary_sensitivity,
    aoi_iou,
    benchmark_fingerprint,
    build_benchmark_report,
    evaluate_aoi_detection,
    fixation_assignment_agreement,
    freeze_benchmark_report,
    match_aois,
)


def test_aoi_iou_and_matching():
    ref = [AOI("r1", "claim", 0, 0, 100, 100)]
    pred = [AOI("p1", "claim", 10, 10, 90, 90)]
    assert aoi_iou(pred[0], ref[0]) == pytest.approx(0.64)
    matched = match_aois(pred, ref, min_iou=0.5)
    assert matched.loc[0, "status"] == "matched"
    metrics = evaluate_aoi_detection(pred, ref, min_iou=0.5)
    assert metrics["precision"] == pytest.approx(1.0)
    assert metrics["recall"] == pytest.approx(1.0)
    assert metrics["semantic_label_accuracy_matched"] == pytest.approx(1.0)


def test_aoi_semantic_mismatch_can_be_required():
    ref = [AOI("r1", "claim", 0, 0, 100, 100)]
    pred = [AOI("p1", "logo", 0, 0, 100, 100)]
    metrics = evaluate_aoi_detection(pred, ref, require_label_match=True)
    assert metrics["true_positive"] == 0
    assert metrics["false_positive"] == 1
    assert metrics["false_negative"] == 1


def test_fixation_assignment_agreement():
    keys = {
        "participant_id": ["p1"] * 4,
        "trial_id": ["t1"] * 4,
        "fixation_index": [0, 1, 2, 3],
    }
    pred = pd.DataFrame({**keys, "aoi_label": ["A", "B", None, "A"]})
    ref = pd.DataFrame({**keys, "aoi_label": ["A", "B", None, "B"]})
    metrics = fixation_assignment_agreement(pred, ref)
    assert metrics["n_aligned_fixations"] == 4
    assert metrics["exact_agreement"] == pytest.approx(0.75)


def test_boundary_sensitivity_is_bounded():
    fixations = pd.DataFrame(
        {
            "x_px": [10, 50, 99, 101],
            "y_px": [10, 50, 99, 101],
        }
    )
    aois = [AOI("a1", "A", 0, 0, 100, 100)]
    out = aoi_boundary_sensitivity(fixations, aois, perturbations_px=(-5, 5))
    assert out["assignment_stability"].between(0, 1).all()
    assert out["assignment_rate"].between(0, 1).all()


def test_benchmark_report_is_deterministic_and_freezes(tmp_path):
    card = BenchmarkDatasetCard(
        name="synthetic-smoke",
        version="1",
        source="generated",
        license="internal-test",
        task="AOI detection smoke test",
        validation_scope="synthetic-smoke-only",
    )
    report1 = build_benchmark_report(benchmark=card, metrics={"f1": 0.9})
    report2 = build_benchmark_report(benchmark=card, metrics={"f1": 0.9})
    assert report1 == report2
    assert report1["report_fingerprint_sha256"] == benchmark_fingerprint(
        {
            "benchmark": card.to_dict(),
            "model": {},
            "protocol": {},
            "metrics": {"f1": 0.9},
        }
    )
    path = freeze_benchmark_report(report1, tmp_path / "report.json")
    assert json.loads(path.read_text(encoding="utf-8"))["metrics"]["f1"] == 0.9
    with pytest.raises(FileExistsError):
        freeze_benchmark_report(report1, path)
