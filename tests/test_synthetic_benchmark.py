from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.synthetic_benchmark import (
    SyntheticGazeSpec,
    build_synthetic_recovery_certificate,
    freeze_synthetic_recovery_certificate,
    score_synthetic_gaze_recovery,
    simulate_known_truth_gaze,
    synthetic_known_truth_gaze_card,
    validate_synthetic_recovery_certificate,
)


def small_spec(**kwargs):
    values = dict(
        n_participants=2,
        n_trials=2,
        samples_per_trial=80,
        sampling_rate_hz=60.0,
        fixation_duration_samples=18,
        saccade_duration_samples=4,
        dropout_probability=0.05,
        random_state=7,
    )
    values.update(kwargs)
    return SyntheticGazeSpec(**values)


def perfect_estimates(run):
    return run.truth.rename(
        columns={"x_true_px": "x_px", "y_true_px": "y_px", "event_label": "predicted_event"}
    )[["participant_id", "trial_id", "sample_index", "x_px", "y_px", "predicted_event"]]


def test_simulation_is_deterministic_and_separates_truth_from_observation():
    first = simulate_known_truth_gaze(small_spec())
    second = simulate_known_truth_gaze(small_spec())
    pd.testing.assert_frame_equal(first.truth, second.truth)
    pd.testing.assert_frame_equal(first.observed_signal, second.observed_signal)
    pd.testing.assert_frame_equal(first.artifact, second.artifact)
    pd.testing.assert_frame_equal(first.event_truth, second.event_truth)
    assert first.contract_fingerprint_sha256 == second.contract_fingerprint_sha256
    assert first.truth[["x_true_px", "y_true_px"]].notna().all().all()
    assert first.observed_signal[["x_px", "y_px"]].isna().any().any()
    assert first.metadata["truth_is_separate_from_observation"] is True
    assert first.metadata["claim_boundary"]["synthetic_validation_only"] is True
    assert first.metadata["claim_boundary"]["empirical_device_validity"] is False


def test_known_truth_card_is_not_human_or_empirical_reference():
    card = synthetic_known_truth_gaze_card(small_spec())
    assert card.annotation_origin == "synthetic"
    assert card.sampling_origin == "synthetic"
    assert card.reference_strength == "synthetic-known-truth"
    assert card.validation_scope == "synthetic-known-truth-method-validation"
    assert card.is_synthetic_known_truth_reference
    assert not card.is_human_reference


def test_seed_changes_contract_and_generated_truth():
    first = simulate_known_truth_gaze(small_spec(random_state=7))
    second = simulate_known_truth_gaze(small_spec(random_state=8))
    assert first.contract_fingerprint_sha256 != second.contract_fingerprint_sha256
    assert not first.truth.equals(second.truth)


def test_event_truth_covers_every_sample_once_as_contiguous_segments():
    run = simulate_known_truth_gaze(small_spec())
    assert set(run.event_truth["event_label"]) == {"fixation", "saccade"}
    total = run.event_truth.groupby(["participant_id", "trial_id"])["n_samples"].sum()
    assert (total == run.spec.samples_per_trial).all()
    assert (run.event_truth["end_sample_index"] >= run.event_truth["start_sample_index"]).all()


def test_perfect_recovery_scores_zero_error_and_perfect_events():
    run = simulate_known_truth_gaze(small_spec())
    metrics = score_synthetic_gaze_recovery(
        run,
        perfect_estimates(run),
        event_col="predicted_event",
    )
    assert metrics["coordinate_rmse_px"] == pytest.approx(0.0)
    assert metrics["coordinate_mae_px"] == pytest.approx(0.0)
    assert metrics["valid_coordinate_fraction"] == pytest.approx(1.0)
    assert metrics["event_accuracy"] == pytest.approx(1.0)
    assert metrics["event_macro_f1"] == pytest.approx(1.0)


def test_recovery_allows_estimate_columns_that_match_truth_names():
    run = simulate_known_truth_gaze(small_spec())
    estimates = run.truth[
        [
            "participant_id",
            "trial_id",
            "sample_index",
            "x_true_px",
            "y_true_px",
            "event_label",
        ]
    ].copy()
    metrics = score_synthetic_gaze_recovery(
        run,
        estimates,
        x_col="x_true_px",
        y_col="y_true_px",
        event_col="event_label",
    )
    assert metrics["coordinate_rmse_px"] == pytest.approx(0.0)
    assert metrics["event_accuracy"] == pytest.approx(1.0)
    assert metrics["event_macro_f1"] == pytest.approx(1.0)


def test_recovery_rejects_reused_estimate_column_selector():
    run = simulate_known_truth_gaze(small_spec())
    estimates = perfect_estimates(run)
    with pytest.raises(ValueError, match="column selectors must be distinct"):
        score_synthetic_gaze_recovery(run, estimates, x_col="x_px", y_col="x_px")


def test_observed_signal_has_nonzero_recovery_error_and_reports_dropout_coverage():
    run = simulate_known_truth_gaze(small_spec())
    metrics = score_synthetic_gaze_recovery(run, run.observed_signal)
    expected_valid = float((~run.artifact["is_dropout"]).mean())
    assert metrics["coordinate_rmse_px"] > 0
    assert metrics["coordinate_mae_px"] > 0
    assert metrics["valid_coordinate_fraction"] == pytest.approx(expected_valid)


def test_recovery_rejects_missing_extra_and_duplicate_keys():
    run = simulate_known_truth_gaze(small_spec())
    estimates = perfect_estimates(run)
    with pytest.raises(ValueError, match="exactly the synthetic truth keys"):
        score_synthetic_gaze_recovery(run, estimates.iloc[:-1].copy())
    duplicate = pd.concat([estimates, estimates.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        score_synthetic_gaze_recovery(run, duplicate)
    extra = estimates.copy()
    extra.loc[len(extra)] = extra.iloc[0]
    extra.loc[len(extra) - 1, "sample_index"] = 9999
    with pytest.raises(ValueError, match="exactly the synthetic truth keys"):
        score_synthetic_gaze_recovery(run, extra)


def test_certificate_is_deterministic_thresholded_and_fail_closed_for_empirical_claims(
    tmp_path: Path,
):
    run = simulate_known_truth_gaze(small_spec())
    estimates = perfect_estimates(run)
    thresholds = {
        "coordinate_rmse_px": 0.1,
        "valid_coordinate_fraction": 1.0,
        "event_macro_f1": 0.99,
    }
    first = build_synthetic_recovery_certificate(
        run,
        estimates,
        estimator_name="perfect-test-estimator",
        event_col="predicted_event",
        thresholds=thresholds,
    )
    second = build_synthetic_recovery_certificate(
        run,
        estimates,
        estimator_name="perfect-test-estimator",
        event_col="predicted_event",
        thresholds=thresholds,
    )
    assert first == second
    assert first["thresholds_passed"] is True
    assert first["claim_boundary"]["synthetic_validation_only"] is True
    assert first["claim_boundary"]["eligible_for_public_frozen_empirical_evidence"] is False
    assert validate_synthetic_recovery_certificate(first, run=run, estimates=estimates)
    path = freeze_synthetic_recovery_certificate(first, tmp_path / "certificate.json")
    assert path.exists()
    with pytest.raises(FileExistsError):
        freeze_synthetic_recovery_certificate(first, path)


def test_certificate_rejects_unknown_threshold_and_failed_threshold_is_not_promoted():
    run = simulate_known_truth_gaze(small_spec())
    estimates = perfect_estimates(run)
    failed = build_synthetic_recovery_certificate(
        run,
        estimates,
        estimator_name="perfect-test-estimator",
        thresholds={"valid_coordinate_fraction": 1.01},
    )
    assert failed["thresholds_passed"] is False
    assert failed["claim_boundary"]["empirical_device_validity"] is False
    with pytest.raises(ValueError, match="Unknown synthetic recovery thresholds"):
        build_synthetic_recovery_certificate(
            run,
            estimates,
            estimator_name="perfect-test-estimator",
            thresholds={"made_up_metric": 1.0},
        )
    with pytest.raises(ValueError, match="must be finite"):
        build_synthetic_recovery_certificate(
            run,
            estimates,
            estimator_name="perfect-test-estimator",
            thresholds={"coordinate_rmse_px": np.inf},
        )


def test_certificate_validation_rejects_resigned_claim_promotion_and_run_drift():
    run = simulate_known_truth_gaze(small_spec())
    estimates = perfect_estimates(run)
    certificate = build_synthetic_recovery_certificate(
        run,
        estimates,
        estimator_name="perfect-test-estimator",
    )
    promoted = dict(certificate)
    promoted["claim_boundary"] = dict(certificate["claim_boundary"])
    promoted["claim_boundary"]["empirical_device_validity"] = True
    body = {k: v for k, v in promoted.items() if k != "certificate_fingerprint_sha256"}
    promoted["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    with pytest.raises(ValueError, match="claim boundary"):
        validate_synthetic_recovery_certificate(promoted)

    other_run = simulate_known_truth_gaze(small_spec(random_state=8))
    with pytest.raises(ValueError, match="does not match run field"):
        validate_synthetic_recovery_certificate(certificate, run=other_run)


def test_freeze_rejects_resigned_claim_promotion_before_writing(tmp_path: Path):
    run = simulate_known_truth_gaze(small_spec())
    certificate = build_synthetic_recovery_certificate(
        run,
        perfect_estimates(run),
        estimator_name="perfect-test-estimator",
    )
    promoted = dict(certificate)
    promoted["claim_boundary"] = dict(certificate["claim_boundary"])
    promoted["claim_boundary"]["empirical_device_validity"] = True
    body = {k: v for k, v in promoted.items() if k != "certificate_fingerprint_sha256"}
    promoted["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    target = tmp_path / "promoted-certificate.json"
    with pytest.raises(ValueError, match="claim boundary"):
        freeze_synthetic_recovery_certificate(promoted, target)
    assert not target.exists()


def test_all_missing_estimates_return_json_safe_null_errors_and_fail_thresholds():
    run = simulate_known_truth_gaze(small_spec())
    estimates = perfect_estimates(run)
    estimates[["x_px", "y_px", "predicted_event"]] = np.nan
    metrics = score_synthetic_gaze_recovery(run, estimates, event_col="predicted_event")
    assert metrics["coordinate_rmse_px"] is None
    assert metrics["event_accuracy"] is None
    certificate = build_synthetic_recovery_certificate(
        run,
        estimates,
        estimator_name="missing-estimator",
        event_col="predicted_event",
        thresholds={"coordinate_rmse_px": 100.0, "event_accuracy": 0.1},
    )
    assert certificate["thresholds_passed"] is False
    assert validate_synthetic_recovery_certificate(certificate, run=run, estimates=estimates)


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"n_participants": 0}, "n_participants"),
        ({"sampling_rate_hz": 0.0}, "sampling_rate_hz"),
        ({"screen_size_px": (0, 1080)}, "screen_size_px"),
        ({"dropout_probability": 1.0}, "dropout_probability"),
        ({"measurement_noise_sd_px": -1.0}, "measurement_noise_sd_px"),
        ({"random_state": -1}, "random_state"),
    ],
)
def test_spec_rejects_invalid_settings(kwargs, message):
    with pytest.raises(ValueError, match=message):
        SyntheticGazeSpec(**kwargs)
