from __future__ import annotations

import pandas as pd
import pytest

from gazeforge.exceptions import SchemaError
from gazeforge.native_agreement import run_native_event_annotator_agreement
from gazeforge.native_event import NativeEventBenchmarkSpec


def _paired_native_data() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    labels_a = [
        "fixation",
        "fixation",
        "fixation",
        "fixation",
        "undefined",
        "fixation",
        "fixation",
        "fixation",
        "saccade",
        "saccade",
        "saccade",
        "saccade",
    ]
    labels_b = labels_a.copy()
    labels_b[7] = "saccade"
    for participant in range(3):
        for annotator, labels in (("expert-a", labels_a), ("expert-b", labels_b)):
            for sample, event_label in enumerate(labels):
                rows.append(
                    {
                        "participant": f"P{participant + 1}",
                        "trial": "T1",
                        "time_ms": sample * (1000.0 / 60.0),
                        "gaze_x": 500.0 + participant * 5.0 + sample,
                        "gaze_y": 350.0 + sample * 0.25,
                        "manual_label": event_label,
                        "annotator": annotator,
                    }
                )
    return pd.DataFrame(rows)


def _spec() -> NativeEventBenchmarkSpec:
    return NativeEventBenchmarkSpec(
        name="native-gp3-agreement-test",
        version="test-1",
        source="synthetic-unit-test-only",
        license="test-only",
        tracker_model="GP3-class test fixture",
        expected_sampling_rate_hz=60.0,
        dataset_status="empirical",
        annotation_origin="expert-manual",
        human_annotator_count=2,
        reference_description="Synthetic expert-like streams for software tests only.",
        column_map={
            "participant_id": "participant",
            "trial_id": "trial",
            "timestamp_ms": "time_ms",
            "x_px": "gaze_x",
            "y_px": "gaze_y",
            "event_label": "manual_label",
            "annotator_id": "annotator",
        },
        analysis_excluded_labels=("undefined",),
        notes=["Synthetic fixture; not empirical validation evidence."],
    )


def test_native_annotator_agreement_is_fingerprinted_and_bidirectional() -> None:
    run = run_native_event_annotator_agreement(
        _paired_native_data(),
        _spec(),
        left_annotator="expert-a",
        right_annotator="expert-b",
        event_min_iou=0.50,
    )

    report = run.report
    all_sample = report["metrics"]["sample_agreement_all_labels"]
    analysis_sample = report["metrics"]["sample_agreement_analysis_labels"]
    left_event = report["metrics"]["event_agreement_left_as_reference"]["summary"]
    right_event = report["metrics"]["event_agreement_right_as_reference"]["summary"]

    assert report["benchmark"]["sampling_origin"] == "native"
    assert report["benchmark"]["human_annotator_count"] == 2
    assert report["protocol"]["underlying_gaze_identity_verified"] is True
    assert report["protocol"]["resampling"] is None
    assert all_sample["exact_agreement"] < 1.0
    assert analysis_sample["n_excluded_pairwise_samples"] == 3
    assert analysis_sample["retained_fraction"] == pytest.approx(33.0 / 36.0)
    assert left_event["n_reference_events"] == 9
    assert left_event["f1"] == pytest.approx(right_event["f1"])
    assert left_event["mean_matched_iou"] == pytest.approx(
        right_event["mean_matched_iou"]
    )
    assert len(report["report_fingerprint_sha256"]) == 64


def test_native_annotator_agreement_rejects_same_annotator() -> None:
    with pytest.raises(ValueError, match="two distinct annotators"):
        run_native_event_annotator_agreement(
            _paired_native_data(),
            _spec(),
            left_annotator="expert-a",
            right_annotator="expert-a",
        )


def test_native_annotator_agreement_rejects_incomplete_sample_alignment() -> None:
    data = _paired_native_data()
    drop_index = data.index[
        (data["annotator"] == "expert-b")
        & (data["participant"] == "P1")
        & (data["time_ms"] == data.loc[1, "time_ms"])
    ][0]
    data = data.drop(index=drop_index).reset_index(drop=True)

    with pytest.raises(SchemaError, match="complete one-to-one sample alignment"):
        run_native_event_annotator_agreement(
            data,
            _spec(),
            left_annotator="expert-a",
            right_annotator="expert-b",
        )


def test_native_annotator_agreement_rejects_different_underlying_gaze() -> None:
    data = _paired_native_data()
    target = data.index[
        (data["annotator"] == "expert-b")
        & (data["participant"] == "P2")
        & (data["time_ms"] == data.loc[2, "time_ms"])
    ][0]
    data.loc[target, "gaze_x"] += 10.0

    with pytest.raises(SchemaError, match="same underlying native gaze samples"):
        run_native_event_annotator_agreement(
            data,
            _spec(),
            left_annotator="expert-a",
            right_annotator="expert-b",
        )
