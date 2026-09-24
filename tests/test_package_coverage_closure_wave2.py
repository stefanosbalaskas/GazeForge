from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import gazeforge.calibration as calibration
import gazeforge.comparison as comparison
import gazeforge.downstream_lineage as downstream
import gazeforge.events as events
import gazeforge.hollywood2_original_subject_metadata as h2meta
import gazeforge.paired as paired
import gazeforge.quality_gating as quality
import gazeforge.resampling as resampling
import gazeforge.schema as schema
import gazeforge.source_resolution_dashboard as source_dashboard
import gazeforge.temporal as temporal
import gazeforge.validation as validation
import gazeforge.validation_scope as validation_scope
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import (
    BenchmarkIntegrityError,
    ModelCompatibilityError,
    SchemaError,
)


def _gaze_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "participant_id": ["P1", "P1", "P2", "P2"],
            "trial_id": ["T1", "T1", "T2", "T2"],
            "sample_index": [0, 1, 0, 1],
            "timestamp_ms": [0.0, 16.6667, 0.0, 16.6667],
            "x_px": [100.0, 101.0, 200.0, 220.0],
            "y_px": [100.0, 100.5, 200.0, 201.0],
            "pupil": [3.0, 3.1, 3.2, 3.3],
            "event_label": ["fixation", "saccade", "fixation", "saccade"],
        }
    )


def _comparison_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "participant_id": ["P1", "P1", "P2", "P2"],
            "trial_id": ["T1", "T1", "T2", "T2"],
            "timestamp_ms": [0.0, 16.6667, 0.0, 16.6667],
            "x_px": [0.0, 1.0, 0.0, 20.0],
            "y_px": [0.0, 0.0, 0.0, 0.0],
            "event_label": ["fixation", "saccade", "fixation", "saccade"],
        }
    )


# ======================================================================
# calibration.py
# ======================================================================


def test_calibration_rejects_missing_probability_columns():
    with pytest.raises(SchemaError, match="No probability columns"):
        calibration._probability_columns(pd.DataFrame({"event_label": ["fixation"]}))


def test_brier_requires_labels_for_array():
    with pytest.raises(ValueError, match="labels are required"):
        calibration.multiclass_brier_score(
            ["fixation"],
            np.array([[1.0, 0.0]]),
        )


@pytest.mark.parametrize(
    ("probabilities", "labels", "match"),
    [
        (
            np.array([1.0, 0.0]),
            ["fixation", "saccade"],
            "2D matrix",
        ),
        (
            np.array([[1.0, 0.0], [0.0, 1.0]]),
            ["fixation", "saccade"],
            "aligned with y_true",
        ),
        (
            np.array([[1.0, 0.0]]),
            ["fixation"],
            "number of probability columns",
        ),
        (
            np.array([[1.1, -0.1]]),
            ["fixation", "saccade"],
            r"\[0, 1\]",
        ),
        (
            np.array([[0.4, 0.4]]),
            ["fixation", "saccade"],
            "sum to 1",
        ),
    ],
)
def test_brier_rejects_invalid_probability_contracts(
    probabilities,
    labels,
    match,
):
    with pytest.raises(ValueError, match=match):
        calibration.multiclass_brier_score(
            ["fixation"],
            probabilities,
            labels=labels,
        )


def test_brier_rejects_unknown_true_label():
    with pytest.raises(
        ValueError,
        match="labels absent from probability columns",
    ):
        calibration.multiclass_brier_score(
            ["blink"],
            np.array([[1.0, 0.0]]),
            labels=["fixation", "saccade"],
        )


def test_calibration_table_rejects_missing_truth():
    predictions = pd.DataFrame(
        {
            "p_event_fixation": [0.8],
            "p_event_saccade": [0.2],
        }
    )

    with pytest.raises(SchemaError, match="Missing true-label"):
        calibration.top_label_calibration_table(predictions)


def test_calibration_table_rejects_too_few_bins():
    predictions = pd.DataFrame(
        {
            "event_label": ["fixation"],
            "p_event_fixation": [1.0],
        }
    )

    with pytest.raises(ValueError, match="n_bins"):
        calibration.top_label_calibration_table(
            predictions,
            n_bins=1,
        )


def test_calibration_table_rejects_non_normalized_rows():
    predictions = pd.DataFrame(
        {
            "event_label": ["fixation"],
            "p_event_fixation": [0.8],
            "p_event_saccade": [0.8],
        }
    )

    with pytest.raises(ValueError, match="sum to 1"):
        calibration.top_label_calibration_table(predictions)


def test_expected_calibration_error_rejects_empty_predictions():
    predictions = pd.DataFrame(
        {
            "event_label": pd.Series(dtype=str),
            "p_event_fixation": pd.Series(dtype=float),
            "p_event_saccade": pd.Series(dtype=float),
        }
    )

    with pytest.raises(ValueError, match="empty prediction table"):
        calibration.expected_calibration_error(predictions)


def test_selective_accuracy_rejects_missing_columns():
    with pytest.raises(SchemaError, match="missing columns"):
        calibration.selective_accuracy_curve(pd.DataFrame({"event_label": ["fixation"]}))


def test_selective_accuracy_rejects_invalid_threshold():
    predictions = pd.DataFrame(
        {
            "event_label": ["fixation"],
            "event_confidence": [0.8],
            "predicted_event": ["fixation"],
        }
    )

    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        calibration.selective_accuracy_curve(
            predictions,
            thresholds=(1.1,),
        )


def test_evaluate_calibration_rejects_missing_truth():
    predictions = pd.DataFrame(
        {
            "p_event_fixation": [0.8],
            "p_event_saccade": [0.2],
        }
    )

    with pytest.raises(SchemaError, match="Missing true-label"):
        calibration.evaluate_event_calibration(predictions)


# ======================================================================
# events.py
# ======================================================================


def test_train_event_classifier_rejects_missing_label():
    frame = _gaze_frame().drop(columns=["event_label"])

    with pytest.raises(SchemaError, match="Missing event label"):
        events.train_event_classifier(
            frame,
            sampling_rate_hz=60.0,
        )


def test_train_event_classifier_rejects_one_class():
    frame = _gaze_frame()
    frame["event_label"] = "fixation"

    with pytest.raises(SchemaError, match="At least two event classes"):
        events.train_event_classifier(
            frame,
            sampling_rate_hz=60.0,
        )


@pytest.mark.parametrize(
    "threshold",
    [0.0, -1.0, np.nan, np.inf],
)
def test_angular_ivt_rejects_invalid_threshold(threshold):
    with pytest.raises(
        ValueError,
        match="finite and positive",
    ):
        events.ivt_classify_events_angular(
            _gaze_frame(),
            sampling_rate_hz=60.0,
            velocity_threshold_deg_s=threshold,
        )


# ======================================================================
# comparison.py
# ======================================================================


def test_fold_metric_row_without_event_level_or_probabilities():
    predictions = pd.DataFrame(
        {
            "event_label": ["fixation", "saccade"],
            "predicted_event": ["fixation", "fixation"],
        }
    )

    row = comparison._fold_metric_row(
        predictions,
        model_name="demo",
        fold=1,
        label_col="event_label",
        n_train_rows=10,
        n_test_rows=2,
        n_train_groups=2,
        n_test_groups=1,
        calibration_bins=10,
        sampling_rate_hz=60.0,
        event_group_cols=("participant_id", "trial_id"),
        event_min_iou=0.5,
        event_excluded_labels=(),
        include_event_level_metrics=False,
    )

    assert np.isnan(row["event_precision"])
    assert np.isnan(row["multiclass_brier_score"])


def test_compare_rejects_missing_required_column():
    with pytest.raises(SchemaError, match="Missing comparison column"):
        comparison.compare_event_models_grouped(
            _comparison_frame().drop(columns=["event_label"]),
            sampling_rate_hz=60.0,
            n_splits=2,
        )


@pytest.mark.parametrize("n_splits", [1, 3])
def test_compare_rejects_invalid_fold_count(n_splits):
    with pytest.raises(ValueError, match="n_splits"):
        comparison.compare_event_models_grouped(
            _comparison_frame(),
            sampling_rate_hz=60.0,
            n_splits=n_splits,
        )


def test_compare_rejects_invalid_calibration_bins():
    with pytest.raises(ValueError, match="calibration_bins"):
        comparison.compare_event_models_grouped(
            _comparison_frame(),
            sampling_rate_hz=60.0,
            n_splits=2,
            calibration_bins=1,
        )


@pytest.mark.parametrize("iou", [-0.1, 1.1])
def test_compare_rejects_invalid_event_iou(iou):
    with pytest.raises(ValueError, match="event_min_iou"):
        comparison.compare_event_models_grouped(
            _comparison_frame(),
            sampling_rate_hz=60.0,
            n_splits=2,
            event_min_iou=iou,
        )


def test_compare_requires_event_grouping_columns_when_enabled():
    frame = _comparison_frame().drop(columns=["trial_id"])

    with pytest.raises(
        SchemaError,
        match="Event-level comparison requires",
    ):
        comparison.compare_event_models_grouped(
            frame,
            sampling_rate_hz=60.0,
            n_splits=2,
            event_group_cols=("participant_id", "trial_id"),
        )


def test_compare_requires_explicit_ivt_threshold_choice():
    with pytest.raises(
        ValueError,
        match="Provide either",
    ):
        comparison.compare_event_models_grouped(
            _comparison_frame(),
            sampling_rate_hz=60.0,
            n_splits=2,
            include_event_level_metrics=False,
            ivt_velocity_threshold_px_s=None,
            ivt_velocity_threshold_deg_s=None,
        )


# ======================================================================
# temporal.py
# ======================================================================


def test_context_matrix_rejects_negative_radius():
    with pytest.raises(ValueError, match="non-negative"):
        temporal._context_matrix(
            _gaze_frame(),
            sampling_rate_hz=60.0,
            context_radius_ms=-1.0,
        )


def test_context_matrix_requires_group_columns():
    frame = _gaze_frame().drop(columns=["trial_id"])

    with pytest.raises(SchemaError, match="grouping columns"):
        temporal._context_matrix(
            frame,
            sampling_rate_hz=60.0,
            context_radius_ms=50.0,
        )


def test_context_matrix_zero_radius_path():
    matrix, names, radius = temporal._context_matrix(
        _gaze_frame(),
        sampling_rate_hz=60.0,
        context_radius_ms=0.0,
    )

    assert radius == 0
    assert matrix.shape[0] == len(_gaze_frame())
    assert matrix.shape[1] == len(names)


def test_train_context_rejects_missing_label():
    with pytest.raises(SchemaError, match="Missing event label"):
        temporal.train_context_event_classifier(
            _gaze_frame().drop(columns=["event_label"]),
            sampling_rate_hz=60.0,
        )


def test_train_context_rejects_one_class():
    frame = _gaze_frame()
    frame["event_label"] = "fixation"

    with pytest.raises(SchemaError, match="At least two event classes"):
        temporal.train_context_event_classifier(
            frame,
            sampling_rate_hz=60.0,
        )


def test_context_classifier_rejects_feature_layout_mismatch():
    model = temporal.TemporalContextModel(
        estimator=object(),
        sampling_rate_hz=60.0,
        context_radius_ms=0.0,
        context_radius_samples=0,
        feature_names=("not-the-real-layout",),
        classes=("fixation", "saccade"),
    )

    with pytest.raises(
        ModelCompatibilityError,
        match="feature layout",
    ):
        temporal.ai_classify_events_context(
            _gaze_frame(),
            model,
            sampling_rate_hz=60.0,
        )


# ======================================================================
# paired.py
# ======================================================================


def test_paired_fold_table_requires_identity_columns():
    with pytest.raises(SchemaError, match="require columns"):
        paired._validate_fold_table(
            pd.DataFrame({"model": ["A"]}),
            model_col="model",
            fold_col="fold",
        )


def test_paired_fold_table_rejects_empty():
    with pytest.raises(ValueError, match="at least one row"):
        paired._validate_fold_table(
            pd.DataFrame(columns=["model", "fold"]),
            model_col="model",
            fold_col="fold",
        )


def test_paired_fold_table_rejects_missing_identifiers():
    with pytest.raises(SchemaError, match="cannot be missing"):
        paired._validate_fold_table(
            pd.DataFrame(
                {
                    "model": ["A"],
                    "fold": [None],
                }
            ),
            model_col="model",
            fold_col="fold",
        )


def test_paired_fold_table_rejects_duplicate_model_fold():
    frame = pd.DataFrame(
        {
            "model": ["A", "A"],
            "fold": [1, 1],
        }
    )

    with pytest.raises(SchemaError, match="at most once"):
        paired._validate_fold_table(
            frame,
            model_col="model",
            fold_col="fold",
        )


def test_paired_rejects_unknown_metric_direction():
    with pytest.raises(ValueError, match="No performance direction"):
        paired._metric_direction("unsupported")


@pytest.mark.parametrize("tolerance", [-1.0, np.nan, np.inf])
def test_paired_rejects_invalid_tie_tolerance(tolerance):
    frame = pd.DataFrame(
        {
            "model": ["A", "B"],
            "fold": [1, 1],
            "accuracy": [0.8, 0.7],
        }
    )

    with pytest.raises(ValueError, match="tie_tolerance"):
        paired.paired_model_metric_differences(
            frame,
            metrics=("accuracy",),
            tie_tolerance=tolerance,
        )


def test_paired_requires_two_models():
    frame = pd.DataFrame(
        {
            "model": ["A"],
            "fold": [1],
            "accuracy": [0.8],
        }
    )

    with pytest.raises(ValueError, match="At least two models"):
        paired.paired_model_metric_differences(
            frame,
            metrics=("accuracy",),
        )


def test_paired_requires_selected_metrics():
    frame = pd.DataFrame(
        {
            "model": ["A", "B"],
            "fold": [1, 1],
        }
    )

    with pytest.raises(ValueError, match="No supported"):
        paired.paired_model_metric_differences(
            frame,
            metrics=(),
        )


def test_paired_rejects_missing_selected_metric():
    frame = pd.DataFrame(
        {
            "model": ["A", "B"],
            "fold": [1, 1],
        }
    )

    with pytest.raises(SchemaError, match="metrics are missing"):
        paired.paired_model_metric_differences(
            frame,
            metrics=("accuracy",),
        )


# ======================================================================
# schema.py
# ======================================================================


def test_sampling_rate_inference_requires_columns():
    with pytest.raises(SchemaError, match="missing columns"):
        schema.infer_sampling_rate_hz(pd.DataFrame({"participant_id": ["P1"]}))


def test_sampling_rate_inference_requires_positive_deltas():
    frame = pd.DataFrame(
        {
            "participant_id": ["P1", "P1"],
            "trial_id": ["T1", "T1"],
            "timestamp_ms": [0.0, 0.0],
        }
    )

    with pytest.raises(
        SchemaError,
        match="non-increasing or insufficient",
    ):
        schema.infer_sampling_rate_hz(frame)


def test_sampling_rate_rejects_invalid_median(monkeypatch):
    frame = pd.DataFrame(
        {
            "participant_id": ["P1", "P1"],
            "trial_id": ["T1", "T1"],
            "timestamp_ms": [0.0, 10.0],
        }
    )

    monkeypatch.setattr(schema.np, "median", lambda values: np.nan)

    with pytest.raises(
        SchemaError,
        match="timestamp interval is invalid",
    ):
        schema.infer_sampling_rate_hz(frame)


def test_canonicalize_requires_dataframe():
    with pytest.raises(SchemaError, match="pandas DataFrame"):
        schema.canonicalize_gaze(
            [],
            sampling_rate_hz=60.0,
        )


def test_canonicalize_rejects_non_numeric_timestamp():
    frame = pd.DataFrame(
        {
            "participant_id": ["P1"],
            "trial_id": ["T1"],
            "timestamp_ms": ["bad"],
            "x_px": [1],
            "y_px": [2],
        }
    )

    with pytest.raises(SchemaError, match="timestamp_ms"):
        schema.canonicalize_gaze(
            frame,
            sampling_rate_hz=60.0,
        )


@pytest.mark.parametrize("rate", [0.0, -1.0, np.nan, np.inf])
def test_canonicalize_rejects_invalid_sampling_rate(rate):
    frame = pd.DataFrame(
        {
            "participant_id": ["P1"],
            "trial_id": ["T1"],
            "timestamp_ms": [0.0],
            "x_px": [1.0],
            "y_px": [2.0],
        }
    )

    with pytest.raises(
        SchemaError,
        match="sampling_rate_hz must be finite and positive",
    ):
        schema.canonicalize_gaze(
            frame,
            sampling_rate_hz=rate,
        )


@pytest.mark.parametrize(
    "size",
    [(0, 1080), (1920, 0), (-1, 1080)],
)
def test_canonicalize_rejects_invalid_screen_size(size):
    frame = pd.DataFrame(
        {
            "participant_id": ["P1"],
            "trial_id": ["T1"],
            "timestamp_ms": [0.0],
            "x_px": [1.0],
            "y_px": [2.0],
        }
    )

    with pytest.raises(SchemaError, match="screen_size_px"):
        schema.canonicalize_gaze(
            frame,
            sampling_rate_hz=60.0,
            screen_size_px=size,
        )


# ======================================================================
# resampling.py
# ======================================================================


def test_interpolation_with_no_finite_source_values():
    result = resampling._interpolate_with_gap_limit(
        np.array([0.0, 10.0]),
        np.array([np.nan, np.nan]),
        np.array([0.0, 5.0, 10.0]),
        max_gap_ms=20.0,
    )

    assert np.isnan(result).all()


def test_majority_window_marks_empty_window_ambiguous():
    labels, purity, source_counts, ambiguous = resampling._majority_label_window(
        np.array([0.0]),
        np.array(["fixation"], dtype=object),
        np.array([1000.0]),
        target_period_ms=10.0,
        min_label_purity=0.75,
        ambiguous_label="ambiguous",
    )

    assert labels == ["ambiguous"]
    assert np.isnan(purity[0])
    assert source_counts[0] == 0
    assert bool(ambiguous[0]) is True


def test_resampling_requires_input_columns():
    with pytest.raises(SchemaError, match="missing columns"):
        resampling.resample_labeled_gaze(
            pd.DataFrame({"participant_id": ["P1"]}),
            source_sampling_rate_hz=500.0,
        )


@pytest.mark.parametrize("rate", [0.0, -1.0])
def test_resampling_rejects_nonpositive_target_rate(rate):
    with pytest.raises(ValueError, match="target_sampling_rate_hz"):
        resampling.resample_labeled_gaze(
            _gaze_frame(),
            target_sampling_rate_hz=rate,
            source_sampling_rate_hz=500.0,
        )


@pytest.mark.parametrize("purity", [0.0, -0.1, 1.1])
def test_resampling_rejects_invalid_label_purity(purity):
    with pytest.raises(ValueError, match="min_label_purity"):
        resampling.resample_labeled_gaze(
            _gaze_frame(),
            target_sampling_rate_hz=60.0,
            source_sampling_rate_hz=500.0,
            min_label_purity=purity,
        )


def test_resampling_rejects_invalid_gap_limit():
    with pytest.raises(ValueError, match="max_interpolation_gap_ms"):
        resampling.resample_labeled_gaze(
            _gaze_frame(),
            target_sampling_rate_hz=60.0,
            source_sampling_rate_hz=500.0,
            max_interpolation_gap_ms=0.0,
        )


def test_resampling_rejects_groups_without_two_timestamps():
    frame = pd.DataFrame(
        {
            "participant_id": ["P1", "P2"],
            "trial_id": ["T1", "T2"],
            "timestamp_ms": [0.0, 0.0],
            "x_px": [1.0, 2.0],
            "y_px": [1.0, 2.0],
            "event_label": ["fixation", "saccade"],
        }
    )

    with pytest.raises(
        SchemaError,
        match="No groups contained enough",
    ):
        resampling.resample_labeled_gaze(
            frame,
            target_sampling_rate_hz=60.0,
            source_sampling_rate_hz=500.0,
        )


# ======================================================================
# validation_scope.py
# ======================================================================


def _scope_partitions():
    train = pd.DataFrame(
        {
            "participant_id": ["P1", "P1"],
            "trial_id": ["T1", "T1"],
            "sample_index": [0, 1],
            "dataset_id": ["D1", "D1"],
        }
    )
    test = pd.DataFrame(
        {
            "participant_id": ["P2", "P2"],
            "trial_id": ["T2", "T2"],
            "sample_index": [0, 1],
            "dataset_id": ["D2", "D2"],
        }
    )
    return train, test


def test_scope_identity_set_rejects_unhashable_values():
    frame = pd.DataFrame(
        {
            "participant_id": [["P1"]],
        }
    )

    with pytest.raises(SchemaError, match="hashable scalar"):
        validation_scope._identity_set(
            frame,
            ("participant_id",),
        )


def test_scope_rejects_duplicate_test_sample_keys():
    train, test = _scope_partitions()
    test.loc[1, "sample_index"] = 0

    with pytest.raises(
        SchemaError,
        match="test partition contains duplicate",
    ):
        validation_scope.derive_validation_scope(train, test)


def test_assert_scope_rejects_unknown_scope():
    train, test = _scope_partitions()
    assessment = validation_scope.derive_validation_scope(
        train,
        test,
    )

    with pytest.raises(ValueError, match="Unknown validation scope"):
        validation_scope.assert_validation_scope(
            assessment,
            "not-a-scope",
        )


def test_validation_scope_certificate_rejects_schema():
    train, test = _scope_partitions()

    with pytest.raises(ValueError, match="Unsupported"):
        validation_scope.validate_validation_scope_certificate(
            {"schema": "bad"},
            train,
            test,
        )


def test_validation_scope_certificate_rejects_missing_fingerprint():
    train, test = _scope_partitions()

    with pytest.raises(ValueError, match="fingerprint"):
        validation_scope.validate_validation_scope_certificate(
            {
                "schema": validation_scope._CERTIFICATE_SCHEMA,
            },
            train,
            test,
        )


def test_validation_scope_certificate_rejects_fingerprint_drift():
    train, test = _scope_partitions()

    with pytest.raises(ValueError, match="fingerprint mismatch"):
        validation_scope.validate_validation_scope_certificate(
            {
                "schema": validation_scope._CERTIFICATE_SCHEMA,
                "certificate_fingerprint_sha256": "a" * 64,
            },
            train,
            test,
        )


def test_validation_scope_certificate_requires_identity_metadata():
    train, test = _scope_partitions()

    body = {
        "schema": validation_scope._CERTIFICATE_SCHEMA,
    }
    certificate = {
        **body,
        "certificate_fingerprint_sha256": benchmark_fingerprint(body),
    }

    with pytest.raises(
        ValueError,
        match="identity-column metadata",
    ):
        validation_scope.validate_validation_scope_certificate(
            certificate,
            train,
            test,
        )


# ======================================================================
# validation.py
# ======================================================================


def test_holdout_indices_require_group_column():
    with pytest.raises(SchemaError, match="Missing grouping column"):
        validation.grouped_holdout_indices(
            pd.DataFrame({"x": [1, 2]}),
        )


def test_leakage_check_requires_columns():
    with pytest.raises(SchemaError, match="Missing leakage-check"):
        validation.assert_no_group_leakage(
            pd.DataFrame({"x": [1]}),
            pd.DataFrame({"x": [2]}),
        )


def test_leakage_check_rejects_overlap():
    train = pd.DataFrame({"participant_id": ["P1", "P2"]})
    test = pd.DataFrame({"participant_id": ["P2", "P3"]})

    with pytest.raises(SchemaError, match="Group leakage"):
        validation.assert_no_group_leakage(train, test)


def test_grouped_event_validation_requires_columns():
    with pytest.raises(SchemaError, match="Missing cross-validation"):
        validation.grouped_event_cross_validate(
            pd.DataFrame({"participant_id": ["P1"]}),
            sampling_rate_hz=60.0,
            n_splits=2,
        )


def test_grouped_event_validation_rejects_fold_count():
    frame = _gaze_frame()

    with pytest.raises(ValueError, match="n_splits"):
        validation.grouped_event_cross_validate(
            frame,
            sampling_rate_hz=60.0,
            n_splits=3,
        )


def test_dataset_holdout_requires_columns():
    with pytest.raises(
        SchemaError,
        match="Dataset-held-out validation is missing",
    ):
        validation.dataset_holdout_event_validate(
            _gaze_frame(),
            sampling_rate_hz=60.0,
        )


def test_dataset_holdout_requires_two_datasets():
    frame = _gaze_frame()
    frame["dataset_id"] = "D1"

    with pytest.raises(ValueError, match="At least two datasets"):
        validation.dataset_holdout_event_validate(
            frame,
            sampling_rate_hz=60.0,
        )


def test_dataset_holdout_can_explicitly_allow_shared_participants(
    monkeypatch,
):
    frame = pd.DataFrame(
        {
            "dataset_id": ["D1", "D1", "D2", "D2"],
            "participant_id": ["P1", "P2", "P1", "P2"],
            "trial_id": ["T1", "T2", "T3", "T4"],
            "timestamp_ms": [0.0, 10.0, 0.0, 10.0],
            "x_px": [0.0, 1.0, 2.0, 3.0],
            "y_px": [0.0, 0.0, 0.0, 0.0],
            "event_label": ["fixation", "saccade", "fixation", "saccade"],
        }
    )

    monkeypatch.setattr(
        validation,
        "train_event_classifier",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        validation,
        "ai_classify_events",
        lambda data, *args, **kwargs: data.assign(predicted_event=data["event_label"].astype(str)),
    )
    monkeypatch.setattr(
        validation,
        "evaluate_event_predictions",
        lambda *args, **kwargs: {"ok": True},
    )

    result = validation.dataset_holdout_event_validate(
        frame,
        sampling_rate_hz=60.0,
        require_disjoint_participants=False,
    )

    assert result.metrics["validation_design"]["require_disjoint_participants"] is False
    assert len(result.folds) == 2


def test_grouped_context_validation_requires_columns():
    with pytest.raises(SchemaError, match="Missing cross-validation"):
        validation.grouped_context_event_cross_validate(
            pd.DataFrame({"participant_id": ["P1"]}),
            sampling_rate_hz=60.0,
            n_splits=2,
        )


def test_grouped_context_validation_rejects_fold_count():
    with pytest.raises(ValueError, match="n_splits"):
        validation.grouped_context_event_cross_validate(
            _gaze_frame(),
            sampling_rate_hz=60.0,
            n_splits=3,
        )


def test_dataset_context_holdout_requires_columns():
    with pytest.raises(
        SchemaError,
        match="Dataset-held-out validation is missing",
    ):
        validation.dataset_holdout_context_event_validate(
            _gaze_frame(),
            sampling_rate_hz=60.0,
        )


def test_dataset_context_holdout_requires_two_datasets():
    frame = _gaze_frame()
    frame["dataset_id"] = "D1"

    with pytest.raises(ValueError, match="At least two datasets"):
        validation.dataset_holdout_context_event_validate(
            frame,
            sampling_rate_hz=60.0,
        )


def test_dataset_context_holdout_can_allow_shared_participants(
    monkeypatch,
):
    frame = pd.DataFrame(
        {
            "dataset_id": ["D1", "D1", "D2", "D2"],
            "participant_id": ["P1", "P2", "P1", "P2"],
            "trial_id": ["T1", "T2", "T3", "T4"],
            "timestamp_ms": [0.0, 10.0, 0.0, 10.0],
            "x_px": [0.0, 1.0, 2.0, 3.0],
            "y_px": [0.0, 0.0, 0.0, 0.0],
            "event_label": ["fixation", "saccade", "fixation", "saccade"],
        }
    )

    monkeypatch.setattr(
        validation,
        "train_context_event_classifier",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        validation,
        "ai_classify_events_context",
        lambda data, *args, **kwargs: data.assign(predicted_event=data["event_label"].astype(str)),
    )
    monkeypatch.setattr(
        validation,
        "evaluate_event_predictions",
        lambda *args, **kwargs: {"ok": True},
    )

    result = validation.dataset_holdout_context_event_validate(
        frame,
        sampling_rate_hz=60.0,
        require_disjoint_participants=False,
    )

    assert result.metrics["validation_design"]["require_disjoint_participants"] is False
    assert len(result.folds) == 2


# ======================================================================
# quality_gating.py
# ======================================================================


def _accelerometer_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "participant_id": ["P1", "P1", "P1"],
            "trial_id": ["T1", "T1", "T1"],
            "timestamp_ms": [0.0, 10.0, 20.0],
            "acc_x": [0.0, 0.1, 0.2],
            "acc_y": [0.0, 0.0, 0.1],
            "acc_z": [1.0, 1.0, 1.0],
            "eda": [1.0, 1.1, 1.2],
        }
    )


def test_quality_column_names_require_nonempty_strings():
    with pytest.raises(ValueError, match="non-empty strings"):
        quality._validate_column_names(
            ("",),
            purpose="Demo",
        )


def test_quality_column_names_require_distinct_names():
    with pytest.raises(ValueError, match="distinct"):
        quality._validate_column_names(
            ("a", "a"),
            purpose="Demo",
        )


@pytest.mark.parametrize("window", [0.0, -1.0, np.nan, np.inf])
def test_motion_index_rejects_invalid_smoothing_window(window):
    with pytest.raises(ValueError, match="smoothing_window_ms"):
        quality.derive_accelerometer_motion_index(
            _accelerometer_frame(),
            smoothing_window_ms=window,
        )


def test_motion_index_rejects_empty_input():
    empty = _accelerometer_frame().iloc[0:0].copy()

    with pytest.raises(SchemaError, match="at least one row"):
        quality.derive_accelerometer_motion_index(empty)


def test_motion_index_rejects_nonfinite_timestamp():
    frame = _accelerometer_frame()
    frame.loc[1, "timestamp_ms"] = np.nan

    with pytest.raises(SchemaError, match="timestamps must be finite"):
        quality.derive_accelerometer_motion_index(frame)


def test_motion_index_rejects_nonincreasing_timestamp():
    frame = _accelerometer_frame()
    frame.loc[1, "timestamp_ms"] = 0.0

    with pytest.raises(
        SchemaError,
        match="strictly increasing",
    ):
        quality.derive_accelerometer_motion_index(frame)


def test_motion_index_supports_intentionally_ungrouped_stream():
    frame = _accelerometer_frame().drop(columns=["participant_id", "trial_id"])

    result = quality.derive_accelerometer_motion_index(
        frame,
        group_cols=(),
    )

    assert "motion_jerk" in result
    assert "motion_index" in result
    assert np.isnan(result.loc[0, "motion_index"])


def test_quality_weight_rejects_negative_motion():
    with pytest.raises(ValueError, match="non-negative"):
        quality.quality_weight_from_motion(
            [0.0, -1.0],
            clean_threshold=1.0,
            severe_threshold=2.0,
        )


def test_motion_quality_gate_requires_modality():
    spec = quality.MotionQualityGateSpec(
        clean_threshold=1.0,
        severe_threshold=2.0,
    )

    with pytest.raises(ValueError, match="modality"):
        quality.apply_motion_quality_gate(
            pd.DataFrame({"motion_index": [0.0]}),
            spec=spec,
            modality="",
        )


def test_motion_quality_gate_rejects_negative_motion():
    spec = quality.MotionQualityGateSpec(
        clean_threshold=1.0,
        severe_threshold=2.0,
    )

    with pytest.raises(ValueError, match="non-negative"):
        quality.apply_motion_quality_gate(
            pd.DataFrame({"motion_index": [-1.0]}),
            spec=spec,
            modality="eda",
        )


def test_motion_certificate_rejects_schema():
    with pytest.raises(ValueError, match="Unsupported"):
        quality.validate_motion_quality_certificate(
            {"schema": "bad"},
            _accelerometer_frame(),
        )


def test_motion_certificate_requires_fingerprint():
    with pytest.raises(ValueError, match="fingerprint"):
        quality.validate_motion_quality_certificate(
            {
                "schema": quality._CERTIFICATE_SCHEMA,
            },
            _accelerometer_frame(),
        )


def test_motion_certificate_rejects_fingerprint_drift():
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        quality.validate_motion_quality_certificate(
            {
                "schema": quality._CERTIFICATE_SCHEMA,
                "certificate_fingerprint_sha256": "a" * 64,
            },
            _accelerometer_frame(),
        )


def test_motion_certificate_rejects_claim_boundary_promotion():
    body = {
        "schema": quality._CERTIFICATE_SCHEMA,
        "claim_boundary": {
            **quality._CLAIM_BOUNDARY,
            "establishes_sensor_validity": True,
        },
    }
    certificate = {
        **body,
        "certificate_fingerprint_sha256": benchmark_fingerprint(body),
    }

    with pytest.raises(ValueError, match="claim boundary"):
        quality.validate_motion_quality_certificate(
            certificate,
            _accelerometer_frame(),
        )


def test_motion_certificate_requires_replay_metadata():
    body = {
        "schema": quality._CERTIFICATE_SCHEMA,
        "claim_boundary": dict(quality._CLAIM_BOUNDARY),
    }
    certificate = {
        **body,
        "certificate_fingerprint_sha256": benchmark_fingerprint(body),
    }

    with pytest.raises(ValueError, match="replay metadata"):
        quality.validate_motion_quality_certificate(
            certificate,
            _accelerometer_frame(),
        )


# ======================================================================
# source_resolution_dashboard.py
# ======================================================================


def _source_summary(dataset_key="demo"):
    return {
        "dataset": "Demo",
        "dataset_key": dataset_key,
        "checked_on": "2026-09-22",
        "status": "unresolved",
        "rights": {
            "analysis_use_terms_status": "unresolved",
            "raw_data_redistribution_terms_status": "unresolved",
        },
        "source_audit_ready": False,
        "empirical_evidence_created": False,
        "record_fingerprint_sha256": "a" * 64,
    }


def test_source_dashboard_row_requires_rights():
    payload = _source_summary()
    payload.pop("rights")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="rights object",
    ):
        source_dashboard._dashboard_row(
            payload,
            "demo.json",
        )


def test_source_dashboard_rejects_duplicate_dataset(
    tmp_path,
    monkeypatch,
):
    first = tmp_path / "a.json"
    second = tmp_path / "b.json"

    monkeypatch.setattr(
        source_dashboard,
        "discover_source_resolution_paths",
        lambda root: (first, second),
    )
    monkeypatch.setattr(
        source_dashboard,
        "validate_source_resolution_records",
        lambda paths: {
            "records": [_source_summary("demo")],
            "bundle_fingerprint_sha256": "b" * 64,
        },
    )
    monkeypatch.setattr(
        source_dashboard,
        "validate_source_resolution_record",
        lambda path: _source_summary("demo"),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="Duplicate source-resolution",
    ):
        source_dashboard.build_source_resolution_dashboard(tmp_path)


def test_source_dashboard_handles_source_outside_root(
    tmp_path,
    monkeypatch,
):
    outside = tmp_path.parent / "outside-source-resolution-demo.json"

    summary = _source_summary("demo")

    monkeypatch.setattr(
        source_dashboard,
        "discover_source_resolution_paths",
        lambda root: (outside,),
    )
    monkeypatch.setattr(
        source_dashboard,
        "validate_source_resolution_records",
        lambda paths: {
            "records": [summary],
            "bundle_fingerprint_sha256": "b" * 64,
        },
    )
    monkeypatch.setattr(
        source_dashboard,
        "validate_source_resolution_record",
        lambda path: summary,
    )

    dashboard = source_dashboard.build_source_resolution_dashboard(tmp_path)

    assert dashboard.source_files == (str(outside),)


def test_source_dashboard_rejects_lock_bundle_mismatch(
    tmp_path,
    monkeypatch,
):
    source = tmp_path / "demo.json"
    summary = _source_summary("demo")

    monkeypatch.setattr(
        source_dashboard,
        "discover_source_resolution_paths",
        lambda root: (source,),
    )
    monkeypatch.setattr(
        source_dashboard,
        "validate_source_resolution_records",
        lambda paths: {
            "records": [summary],
            "bundle_fingerprint_sha256": "b" * 64,
        },
    )
    monkeypatch.setattr(
        source_dashboard,
        "validate_source_resolution_record",
        lambda path: summary,
    )
    monkeypatch.setattr(
        source_dashboard,
        "validate_source_resolution_bundle_lock",
        lambda lock, directory: {
            "bundle_fingerprint_sha256": "c" * 64,
            "reviewed_on": "2026-09-22",
            "lock_fingerprint_sha256": "d" * 64,
        },
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="does not identify",
    ):
        source_dashboard.build_source_resolution_dashboard(
            tmp_path,
            lock_path=tmp_path / "lock.json",
        )


def test_source_dashboard_render_rejects_incomplete_review_metadata():
    dashboard = source_dashboard.SourceResolutionDashboard(
        records=(),
        rows=(),
        source_files=(),
        bundle_fingerprint_sha256="a" * 64,
        reviewed_snapshot=True,
        reviewed_on=None,
        lock_fingerprint_sha256=None,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="missing reviewed lock metadata",
    ):
        source_dashboard.render_source_resolution_dashboard_markdown(dashboard)


# ======================================================================
# Hollywood2 public metadata tiny residual
# ======================================================================


def test_hollywood2_page_summary_handles_decode_attribute_error():
    class BrokenDecodeBytes(bytes):
        def decode(self, *args, **kwargs):
            raise AttributeError("decode unavailable")

    result = h2meta._page_summary(
        {
            "http_status": 200,
            "body": BrokenDecodeBytes(b"broken"),
        },
        base_url=h2meta.DESCRIPTION_URL,
    )

    assert result["normalized_text_length"] == 0
    assert result["normalized_text"] == ""


# ======================================================================
# downstream_lineage.py - remaining type guards
# ======================================================================


def test_downstream_binding_requires_lineage_instance():
    with pytest.raises(
        TypeError,
        match="lineage must be",
    ):
        downstream.validate_source_audit_lineage_binding(
            None,
            dataset_key="demo",
            audit_report_fingerprint_sha256="a" * 64,
            authorized_spec_fingerprint_sha256="b" * 64,
            source_manifest_fingerprints_sha256={"source": "c" * 64},
            source_revision="rev",
        )


def test_downstream_giw_binding_requires_audit_instance():
    with pytest.raises(
        TypeError,
        match="audit must be",
    ):
        downstream.validate_gaze_in_wild_audit_lineage(
            None,
            None,
        )


def test_downstream_hollywood_binding_requires_gaze_instance():
    with pytest.raises(
        TypeError,
        match="gaze must be",
    ):
        downstream.validate_hollywood2_gaze_lineage(
            None,
            None,
        )
