from __future__ import annotations

import copy
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from test_visus_validation import _audit, _inputs

import gazeforge.visus_validation as visval
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.dynamic_aoi import DynamicAOIKeyframe
from gazeforge.exceptions import BenchmarkIntegrityError, SchemaError


def _resign_audit_report(audit) -> None:
    body = {key: value for key, value in audit.report.items() if key != "report_fingerprint_sha256"}
    audit.report["report_fingerprint_sha256"] = benchmark_fingerprint(body)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("model", True),
        ("  model  ", True),
        ("", False),
        ("   ", False),
        ("REPLACE_ME", False),
        ("please verify", False),
    ],
)
def test_resolved_contract(value: str, expected: bool) -> None:
    assert visval._resolved(value) is expected


def test_verify_audit_integrity_type_and_status_guards(tmp_path) -> None:
    with pytest.raises(
        TypeError,
        match="VisusSourceAuditRun",
    ):
        visval._verify_audit_integrity(object())

    audit = _audit(tmp_path / "status")
    audit.report["status"] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="not verified",
    ):
        visval._verify_audit_integrity(audit)


def test_verify_audit_integrity_report_fingerprint_guard(tmp_path) -> None:
    audit = _audit(tmp_path)

    audit.report["report_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="report fingerprint",
    ):
        visval._verify_audit_integrity(audit)


def test_verify_audit_integrity_spec_fingerprint_guard(tmp_path) -> None:
    audit = _audit(tmp_path)

    audit.report["spec_fingerprint_sha256"] = "0" * 64
    _resign_audit_report(audit)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="specification fingerprint",
    ):
        visval._verify_audit_integrity(audit)


def test_verify_audit_integrity_manifest_fingerprint_guard(tmp_path) -> None:
    audit = _audit(tmp_path)

    audit.report["inventory"]["manifest_fingerprint_sha256"] = "0" * 64
    _resign_audit_report(audit)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="manifest fingerprint",
    ):
        visval._verify_audit_integrity(audit)


def test_audited_stimuli_success_and_empty(tmp_path) -> None:
    audit = _audit(tmp_path)

    stimuli = visval._audited_stimuli(audit)

    assert len(stimuli) == 11
    assert stimuli == sorted(stimuli)

    audit.report["identity"]["stimulus_ids"] = []

    with pytest.raises(
        BenchmarkIntegrityError,
        match="no verified stimulus identities",
    ):
        visval._audited_stimuli(audit)


def test_validate_exact_keys_success_missing_and_extra() -> None:
    visval._validate_exact_keys(
        {"S01": 1, "S02": 2},
        ["S01", "S02"],
        name="fixture",
    )

    with pytest.raises(
        SchemaError,
        match="missing=",
    ):
        visval._validate_exact_keys(
            {"S01": 1},
            ["S01", "S02"],
            name="fixture",
        )

    with pytest.raises(
        SchemaError,
        match="extra=",
    ):
        visval._validate_exact_keys(
            {"S01": 1, "S02": 2, "S99": 3},
            ["S01", "S02"],
            name="fixture",
        )


def test_validate_reference_stream_empty_guard(tmp_path) -> None:
    audit = _audit(tmp_path)

    with pytest.raises(
        ValueError,
        match="cannot be empty",
    ):
        visval._validate_reference_stream(
            audit,
            reference_stream_id=" ",
            stimuli=visval._audited_stimuli(audit),
        )


def test_validate_reference_stream_missing_guard(tmp_path) -> None:
    audit = _audit(tmp_path)

    with pytest.raises(
        SchemaError,
        match="not manifested",
    ):
        visval._validate_reference_stream(
            audit,
            reference_stream_id="missing",
            stimuli=visval._audited_stimuli(audit),
        )


def test_validate_reference_stream_success(tmp_path) -> None:
    audit = _audit(tmp_path)

    visval._validate_reference_stream(
        audit,
        reference_stream_id="published_curated",
        stimuli=visval._audited_stimuli(audit),
    )


def _frame(
    *,
    model_name: str | None = None,
    model_version: str | None = None,
) -> DynamicAOIKeyframe:
    return DynamicAOIKeyframe(
        "target",
        "person",
        0.0,
        0.0,
        0.0,
        100.0,
        100.0,
        model_name=model_name,
        model_version=model_version,
    )


def test_validate_keyframes_reference_empty_guard() -> None:
    with pytest.raises(
        SchemaError,
        match="reference keyframes are empty",
    ):
        visval._validate_keyframes(
            [],
            kind="reference",
            stimulus_id="S01",
            model_name="Model",
            model_version="1",
        )


def test_validate_keyframes_wrong_type_guard() -> None:
    with pytest.raises(
        TypeError,
        match="DynamicAOIKeyframe",
    ):
        visval._validate_keyframes(
            [object()],
            kind="predicted",
            stimulus_id="S01",
            model_name="Model",
            model_version="1",
        )


def test_validate_keyframes_model_name_guard() -> None:
    with pytest.raises(
        SchemaError,
        match="model_name mismatch",
    ):
        visval._validate_keyframes(
            [_frame(model_name="Wrong", model_version="1")],
            kind="predicted",
            stimulus_id="S01",
            model_name="Model",
            model_version="1",
        )


def test_validate_keyframes_model_version_guard() -> None:
    with pytest.raises(
        SchemaError,
        match="model_version mismatch",
    ):
        visval._validate_keyframes(
            [_frame(model_name="Model", model_version="2")],
            kind="predicted",
            stimulus_id="S01",
            model_name="Model",
            model_version="1",
        )


def test_validate_keyframes_predicted_optional_provenance_success() -> None:
    result = visval._validate_keyframes(
        [_frame()],
        kind="predicted",
        stimulus_id="S01",
        model_name="Model",
        model_version="1",
    )

    assert len(result) == 1


def test_json_records_normalizes_nan_to_none() -> None:
    frame = pd.DataFrame(
        {
            "x": [1.0, np.nan],
            "label": ["a", None],
        }
    )

    records = visval._json_records(frame)

    assert records == [
        {"x": 1.0, "label": "a"},
        {"x": None, "label": None},
    ]


def _evaluation(
    *,
    tp: int,
    fp: int,
    fn: int,
    matches: pd.DataFrame | None = None,
):
    if matches is None:
        matches = pd.DataFrame(
            columns=[
                "status",
                "iou",
                "label_match",
            ]
        )

    return SimpleNamespace(
        summary={
            "true_positive": tp,
            "false_positive": fp,
            "false_negative": fn,
            "n_timestamps": 1,
            "n_empty_timestamps": 0,
            "predicted_track_timepoints": tp + fp,
            "reference_track_timepoints": tp + fn,
        },
        matches=matches,
    )


def test_aggregate_evaluations_zero_denominator_defaults() -> None:
    result = visval._aggregate_evaluations(
        {
            "S01": _evaluation(
                tp=0,
                fp=0,
                fn=0,
            )
        }
    )

    assert result["precision"] == 1.0
    assert result["recall"] == 1.0
    assert result["f1"] == 1.0
    assert result["mean_matched_iou"] == 0.0
    assert result["semantic_label_accuracy_matched"] == 0.0


def test_aggregate_evaluations_zero_f1_branch() -> None:
    result = visval._aggregate_evaluations(
        {
            "S01": _evaluation(
                tp=0,
                fp=1,
                fn=1,
            )
        }
    )

    assert result["precision"] == 0.0
    assert result["recall"] == 0.0
    assert result["f1"] == 0.0


def test_aggregate_evaluations_matched_metrics() -> None:
    matches = pd.DataFrame(
        {
            "status": [
                "matched",
                "matched",
                "false_positive",
            ],
            "iou": [
                0.5,
                1.0,
                0.0,
            ],
            "label_match": [
                True,
                False,
                False,
            ],
        }
    )

    result = visval._aggregate_evaluations(
        {
            "S01": _evaluation(
                tp=2,
                fp=1,
                fn=1,
                matches=matches,
            )
        }
    )

    assert result["mean_matched_iou"] == pytest.approx(0.75)
    assert result["semantic_label_accuracy_matched"] == pytest.approx(0.5)


def test_combined_fixation_assignment_missing_columns_guard() -> None:
    predictions, references, _, _ = _inputs()

    fixations = {
        "S01": pd.DataFrame(
            {
                "timestamp_ms": [0.0],
                "x_px": [1.0],
            }
        )
    }

    with pytest.raises(
        SchemaError,
        match="missing columns",
    ):
        visval._combined_fixation_assignment(
            fixations,
            predictions,
            references,
            stimuli=["S01"],
            max_interpolation_gap_ms=100.0,
            overlap_rule="highest_confidence",
        )


def test_combined_fixation_assignment_empty_guard() -> None:
    predictions, references, _, _ = _inputs()

    fixations = {
        "S01": pd.DataFrame(
            columns=[
                "timestamp_ms",
                "x_px",
                "y_px",
            ]
        )
    }

    with pytest.raises(
        SchemaError,
        match="is empty",
    ):
        visval._combined_fixation_assignment(
            fixations,
            predictions,
            references,
            stimuli=["S01"],
            max_interpolation_gap_ms=100.0,
            overlap_rule="highest_confidence",
        )


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        (
            "model_name",
            "REPLACE_ME",
            "model_name and model_version",
        ),
        (
            "model_version",
            "VERIFY",
            "model_name and model_version",
        ),
        (
            "timestamp_grid_basis",
            "REPLACE",
            "timestamp_grid_basis",
        ),
        (
            "max_interpolation_gap_ms",
            float("nan"),
            "finite and non-negative",
        ),
        (
            "max_interpolation_gap_ms",
            -1.0,
            "finite and non-negative",
        ),
        (
            "min_iou",
            float("nan"),
            "finite and in",
        ),
        (
            "min_iou",
            -0.1,
            "finite and in",
        ),
        (
            "min_iou",
            1.1,
            "finite and in",
        ),
    ],
)
def test_run_parameter_guards(
    tmp_path,
    field: str,
    value,
    match: str,
) -> None:
    audit = _audit(tmp_path)
    predictions, references, timestamps, _ = _inputs()

    kwargs = {
        "predicted_by_stimulus": predictions,
        "reference_by_stimulus": references,
        "timestamps_by_stimulus": timestamps,
        "reference_stream_id": "published_curated",
        "model_name": "FixtureTracker",
        "model_version": "1.0",
        "timestamp_grid_basis": "fixture timestamps",
        "max_interpolation_gap_ms": 100.0,
        "min_iou": 0.5,
    }

    kwargs[field] = value

    with pytest.raises(
        ValueError,
        match=match,
    ):
        visval.run_visus_dynamic_aoi_model_validation(
            audit,
            **kwargs,
        )


def test_run_rejects_extra_reference_coverage(tmp_path) -> None:
    audit = _audit(tmp_path)
    predictions, references, timestamps, _ = _inputs()

    references["S99"] = copy.deepcopy(references["S01"])

    with pytest.raises(
        SchemaError,
        match="extra=",
    ):
        visval.run_visus_dynamic_aoi_model_validation(
            audit,
            predicted_by_stimulus=predictions,
            reference_by_stimulus=references,
            timestamps_by_stimulus=timestamps,
            reference_stream_id="published_curated",
            model_name="FixtureTracker",
            model_version="1.0",
            timestamp_grid_basis="fixture timestamps",
            max_interpolation_gap_ms=100.0,
        )


def test_run_rejects_incomplete_timestamp_coverage(tmp_path) -> None:
    audit = _audit(tmp_path)
    predictions, references, timestamps, _ = _inputs()

    timestamps.pop("S11")

    with pytest.raises(
        SchemaError,
        match="timestamp grids",
    ):
        visval.run_visus_dynamic_aoi_model_validation(
            audit,
            predicted_by_stimulus=predictions,
            reference_by_stimulus=references,
            timestamps_by_stimulus=timestamps,
            reference_stream_id="published_curated",
            model_name="FixtureTracker",
            model_version="1.0",
            timestamp_grid_basis="fixture timestamps",
            max_interpolation_gap_ms=100.0,
        )


def test_run_rejects_incomplete_fixation_coverage(tmp_path) -> None:
    audit = _audit(tmp_path)
    predictions, references, timestamps, fixations = _inputs()

    fixations.pop("S11")

    with pytest.raises(
        SchemaError,
        match="fixation tables",
    ):
        visval.run_visus_dynamic_aoi_model_validation(
            audit,
            predicted_by_stimulus=predictions,
            reference_by_stimulus=references,
            timestamps_by_stimulus=timestamps,
            fixations_by_stimulus=fixations,
            reference_stream_id="published_curated",
            model_name="FixtureTracker",
            model_version="1.0",
            timestamp_grid_basis="fixture timestamps",
            max_interpolation_gap_ms=100.0,
        )


def test_run_reference_empty_guard(tmp_path) -> None:
    audit = _audit(tmp_path)
    predictions, references, timestamps, _ = _inputs()

    references["S01"] = []

    with pytest.raises(
        SchemaError,
        match="reference keyframes are empty",
    ):
        visval.run_visus_dynamic_aoi_model_validation(
            audit,
            predicted_by_stimulus=predictions,
            reference_by_stimulus=references,
            timestamps_by_stimulus=timestamps,
            reference_stream_id="published_curated",
            model_name="FixtureTracker",
            model_version="1.0",
            timestamp_grid_basis="fixture timestamps",
            max_interpolation_gap_ms=100.0,
        )


def test_run_predicted_wrong_type_guard(tmp_path) -> None:
    audit = _audit(tmp_path)
    predictions, references, timestamps, _ = _inputs()

    predictions["S01"] = [object()]

    with pytest.raises(
        TypeError,
        match="DynamicAOIKeyframe",
    ):
        visval.run_visus_dynamic_aoi_model_validation(
            audit,
            predicted_by_stimulus=predictions,
            reference_by_stimulus=references,
            timestamps_by_stimulus=timestamps,
            reference_stream_id="published_curated",
            model_name="FixtureTracker",
            model_version="1.0",
            timestamp_grid_basis="fixture timestamps",
            max_interpolation_gap_ms=100.0,
        )


def test_run_predicted_model_name_guard(tmp_path) -> None:
    audit = _audit(tmp_path)
    predictions, references, timestamps, _ = _inputs()

    predictions["S01"][0] = replace(
        predictions["S01"][0],
        model_name="WrongModel",
    )

    with pytest.raises(
        SchemaError,
        match="model_name mismatch",
    ):
        visval.run_visus_dynamic_aoi_model_validation(
            audit,
            predicted_by_stimulus=predictions,
            reference_by_stimulus=references,
            timestamps_by_stimulus=timestamps,
            reference_stream_id="published_curated",
            model_name="FixtureTracker",
            model_version="1.0",
            timestamp_grid_basis="fixture timestamps",
            max_interpolation_gap_ms=100.0,
        )


def test_run_predicted_model_version_guard(tmp_path) -> None:
    audit = _audit(tmp_path)
    predictions, references, timestamps, _ = _inputs()

    predictions["S01"][0] = replace(
        predictions["S01"][0],
        model_version="wrong",
    )

    with pytest.raises(
        SchemaError,
        match="model_version mismatch",
    ):
        visval.run_visus_dynamic_aoi_model_validation(
            audit,
            predicted_by_stimulus=predictions,
            reference_by_stimulus=references,
            timestamps_by_stimulus=timestamps,
            reference_stream_id="published_curated",
            model_name="FixtureTracker",
            model_version="1.0",
            timestamp_grid_basis="fixture timestamps",
            max_interpolation_gap_ms=100.0,
        )


def test_run_without_fixations_or_matches_success(tmp_path) -> None:
    audit = _audit(tmp_path)
    predictions, references, timestamps, _ = _inputs()

    run = visval.run_visus_dynamic_aoi_model_validation(
        audit,
        predicted_by_stimulus=predictions,
        reference_by_stimulus=references,
        timestamps_by_stimulus=timestamps,
        reference_stream_id="published_curated",
        model_name="FixtureTracker",
        model_version="1.0",
        timestamp_grid_basis="fixture timestamps",
        max_interpolation_gap_ms=100.0,
        include_matches=False,
    )

    assert run.fixation_assignment is None
    assert run.matches.empty
    assert "matches" not in run.report["metrics"]
    assert run.report["protocol"]["fixation_assignment_enabled"] is False


def test_run_with_matches_but_without_fixations_success(tmp_path) -> None:
    audit = _audit(tmp_path)
    predictions, references, timestamps, _ = _inputs()

    run = visval.run_visus_dynamic_aoi_model_validation(
        audit,
        predicted_by_stimulus=predictions,
        reference_by_stimulus=references,
        timestamps_by_stimulus=timestamps,
        reference_stream_id="published_curated",
        model_name="FixtureTracker",
        model_version="1.0",
        timestamp_grid_basis="fixture timestamps",
        max_interpolation_gap_ms=100.0,
        include_matches=True,
    )

    assert run.fixation_assignment is None
    assert not run.matches.empty
    assert "matches" in run.report["metrics"]
