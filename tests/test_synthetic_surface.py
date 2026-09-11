from pathlib import Path

import pandas as pd
import pytest

from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.synthetic_benchmark import SyntheticGazeSpec
from gazeforge.synthetic_surface import (
    SyntheticGazeSurfaceSpec,
    evaluate_synthetic_recovery_surface,
    expand_synthetic_gaze_surface,
    freeze_synthetic_recovery_surface,
    validate_synthetic_recovery_surface,
)


def base_spec(**kwargs):
    values = dict(
        n_participants=1,
        n_trials=1,
        samples_per_trial=48,
        sampling_rate_hz=60.0,
        fixation_duration_samples=12,
        saccade_duration_samples=4,
        fixation_sd_px=0.0,
        measurement_noise_sd_px=0.0,
        pupil_noise_sd_mm=0.0,
        calibration_bias_px=(0.0, 0.0),
        dropout_probability=0.0,
        random_state=11,
    )
    values.update(kwargs)
    return SyntheticGazeSpec(**values)


def identity_estimator(observed: pd.DataFrame) -> pd.DataFrame:
    return observed[["participant_id", "trial_id", "sample_index", "x_px", "y_px"]].copy()


def two_noise_surface(**kwargs):
    values = dict(
        base_spec=base_spec(),
        measurement_noise_sd_px=(0.0, 15.0),
        max_conditions=8,
    )
    values.update(kwargs)
    return SyntheticGazeSurfaceSpec(**values)


def _resign_surface(certificate):
    body = {k: v for k, v in certificate.items() if k != "surface_fingerprint_sha256"}
    certificate["surface_fingerprint_sha256"] = benchmark_fingerprint(body)


def test_surface_axes_are_sorted_unique_and_condition_ids_are_order_invariant():
    first = SyntheticGazeSurfaceSpec(
        base_spec=base_spec(),
        measurement_noise_sd_px=(15.0, 0.0, 15.0),
        dropout_probabilities=(0.1, 0.0, 0.1),
        random_states=(12, 11, 12),
        max_conditions=16,
    )
    second = SyntheticGazeSurfaceSpec(
        base_spec=base_spec(),
        measurement_noise_sd_px=(0.0, 15.0),
        dropout_probabilities=(0.0, 0.1),
        random_states=(11, 12),
        max_conditions=16,
    )
    assert first.to_dict() == second.to_dict()
    assert first.condition_count == 8
    assert [c.condition_id for c in expand_synthetic_gaze_surface(first)] == [
        c.condition_id for c in expand_synthetic_gaze_surface(second)
    ]


def test_surface_rejects_factorial_explosion_before_execution():
    with pytest.raises(ValueError, match="exceeds max_conditions"):
        SyntheticGazeSurfaceSpec(
            base_spec=base_spec(),
            measurement_noise_sd_px=(0.0, 5.0),
            dropout_probabilities=(0.0, 0.1),
            random_states=(1, 2),
            max_conditions=7,
        )


def test_surface_reuses_single_spec_guards_for_invalid_axes():
    with pytest.raises(ValueError, match="dropout_probability"):
        SyntheticGazeSurfaceSpec(
            base_spec=base_spec(),
            dropout_probabilities=(0.0, 1.0),
        )
    with pytest.raises(ValueError, match="measurement_noise_sd_px"):
        SyntheticGazeSurfaceSpec(
            base_spec=base_spec(),
            measurement_noise_sd_px=(-1.0, 0.0),
        )
    with pytest.raises(ValueError, match="values must be integers"):
        SyntheticGazeSurfaceSpec(
            base_spec=base_spec(),
            fixation_duration_samples=(4, 4.5),
        )


def test_surface_estimator_receives_observed_signal_only():
    seen_columns = []

    def estimator(observed):
        seen_columns.append(set(observed.columns))
        assert "x_true_px" not in observed.columns
        assert "y_true_px" not in observed.columns
        assert "event_label" not in observed.columns
        assert "is_dropout" not in observed.columns
        return identity_estimator(observed)

    result = evaluate_synthetic_recovery_surface(
        two_noise_surface(),
        estimator,
        estimator_name="identity-observation-baseline",
    )
    assert len(seen_columns) == 2
    contract = result.surface_certificate["estimator"]
    assert contract["callback_input"] == "observed_signal_only"
    assert contract["latent_truth_passed_to_callback"] is False
    assert contract["artifact_ledger_passed_to_callback"] is False


def test_identity_baseline_maps_expected_noise_robustness_surface():
    result = evaluate_synthetic_recovery_surface(
        two_noise_surface(),
        identity_estimator,
        estimator_name="identity-observation-baseline",
    )
    ledger = result.condition_ledger
    assert len(ledger) == 2
    by_noise = {
        row["spec"]["measurement_noise_sd_px"]: row["metrics"]["coordinate_rmse_px"]
        for row in ledger.to_dict(orient="records")
    }
    assert by_noise[0.0] == pytest.approx(0.0)
    assert by_noise[15.0] > by_noise[0.0]
    summary = result.surface_certificate["metric_summary"]["coordinate_rmse_px"]
    assert summary["n_finite"] == 2
    assert summary["min"] == pytest.approx(0.0)
    assert summary["max"] == pytest.approx(by_noise[15.0])


def test_surface_is_deterministic_for_same_design_and_estimator_outputs():
    first = evaluate_synthetic_recovery_surface(
        two_noise_surface(),
        identity_estimator,
        estimator_name="identity-observation-baseline",
        thresholds={"coordinate_rmse_px": 30.0, "valid_coordinate_fraction": 1.0},
    )
    second = evaluate_synthetic_recovery_surface(
        two_noise_surface(),
        identity_estimator,
        estimator_name="identity-observation-baseline",
        thresholds={"coordinate_rmse_px": 30.0, "valid_coordinate_fraction": 1.0},
    )
    assert first.surface_certificate == second.surface_certificate
    assert first.surface_fingerprint_sha256 == second.surface_fingerprint_sha256
    pd.testing.assert_frame_equal(first.condition_ledger, second.condition_ledger)
    assert validate_synthetic_recovery_surface(first.surface_certificate)


def test_surface_threshold_overview_counts_pass_and_fail_conditions():
    result = evaluate_synthetic_recovery_surface(
        two_noise_surface(),
        identity_estimator,
        estimator_name="identity-observation-baseline",
        thresholds={"coordinate_rmse_px": 1.0},
    )
    overview = result.surface_certificate["threshold_overview"]
    assert overview == {
        "thresholded_conditions": 2,
        "passed_conditions": 1,
        "failed_conditions": 1,
        "pass_fraction": 0.5,
        "unthresholded_conditions": 0,
    }


def test_surface_supports_explicit_replicate_seeds_with_common_condition_design():
    surface = SyntheticGazeSurfaceSpec(
        base_spec=base_spec(),
        measurement_noise_sd_px=(5.0, 10.0),
        random_states=(11, 12, 13),
        max_conditions=8,
    )
    conditions = expand_synthetic_gaze_surface(surface)
    assert len(conditions) == 6
    assert {condition.spec.random_state for condition in conditions} == {11, 12, 13}
    assert surface.to_dict()["common_random_numbers_within_seed"] is True


def test_surface_rejects_non_dataframe_estimator_output():
    with pytest.raises(TypeError, match="must return a pandas DataFrame"):
        evaluate_synthetic_recovery_surface(
            SyntheticGazeSurfaceSpec(base_spec=base_spec()),
            lambda observed: observed.to_dict(),
            estimator_name="invalid-estimator",
        )


def test_validator_rejects_resigned_empirical_claim_promotion():
    result = evaluate_synthetic_recovery_surface(
        two_noise_surface(),
        identity_estimator,
        estimator_name="identity-observation-baseline",
    )
    promoted = dict(result.surface_certificate)
    promoted["claim_boundary"] = dict(promoted["claim_boundary"])
    promoted["claim_boundary"]["empirical_device_validity"] = True
    _resign_surface(promoted)
    with pytest.raises(ValueError, match="claim boundary"):
        validate_synthetic_recovery_surface(promoted)


def test_validator_rejects_resigned_condition_inventory_tamper():
    result = evaluate_synthetic_recovery_surface(
        two_noise_surface(),
        identity_estimator,
        estimator_name="identity-observation-baseline",
    )
    tampered = dict(result.surface_certificate)
    tampered["condition_ledger"] = [dict(row) for row in tampered["condition_ledger"]]
    tampered["condition_ledger"][0]["condition_spec_sha256"] = "0" * 64
    _resign_surface(tampered)
    with pytest.raises(ValueError, match="condition-spec fingerprint"):
        validate_synthetic_recovery_surface(tampered, replay_contracts=False)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("condition_count", 999),
        ("design", "forged-design"),
        ("common_random_numbers_within_seed", False),
    ],
)
def test_validator_rejects_resigned_noncanonical_surface_spec_metadata(field, value):
    result = evaluate_synthetic_recovery_surface(
        two_noise_surface(),
        identity_estimator,
        estimator_name="identity-observation-baseline",
    )
    tampered = dict(result.surface_certificate)
    tampered["surface_spec"] = dict(tampered["surface_spec"])
    tampered["surface_spec"][field] = value
    _resign_surface(tampered)
    with pytest.raises(ValueError, match="specification is not canonical"):
        validate_synthetic_recovery_surface(tampered, replay_contracts=False)


def test_validator_rejects_resigned_child_claim_promotion():
    result = evaluate_synthetic_recovery_surface(
        two_noise_surface(),
        identity_estimator,
        estimator_name="identity-observation-baseline",
    )
    tampered = dict(result.surface_certificate)
    tampered["child_certificates"] = {
        key: dict(value) for key, value in tampered["child_certificates"].items()
    }
    condition_id = next(iter(tampered["child_certificates"]))
    child = tampered["child_certificates"][condition_id]
    child["claim_boundary"] = dict(child["claim_boundary"])
    child["claim_boundary"]["human_reference_ground_truth"] = True
    child_body = {
        key: value for key, value in child.items() if key != "certificate_fingerprint_sha256"
    }
    child["certificate_fingerprint_sha256"] = benchmark_fingerprint(child_body)
    for row in tampered["condition_ledger"]:
        if row["condition_id"] == condition_id:
            row["child_certificate_fingerprint_sha256"] = child[
                "certificate_fingerprint_sha256"
            ]
            break
    _resign_surface(tampered)
    with pytest.raises(ValueError, match="claim boundary"):
        validate_synthetic_recovery_surface(tampered, replay_contracts=False)


def test_freeze_validates_surface_before_writing_and_protects_existing_file(tmp_path: Path):
    result = evaluate_synthetic_recovery_surface(
        two_noise_surface(),
        identity_estimator,
        estimator_name="identity-observation-baseline",
    )
    target = tmp_path / "surface.json"
    frozen = freeze_synthetic_recovery_surface(result.surface_certificate, target)
    assert frozen == target
    assert target.exists()
    with pytest.raises(FileExistsError):
        freeze_synthetic_recovery_surface(result.surface_certificate, target)

    promoted = dict(result.surface_certificate)
    promoted["claim_boundary"] = dict(promoted["claim_boundary"])
    promoted["claim_boundary"]["empirical_device_validity"] = True
    _resign_surface(promoted)
    blocked = tmp_path / "promoted.json"
    with pytest.raises(ValueError, match="claim boundary"):
        freeze_synthetic_recovery_surface(promoted, blocked)
    assert not blocked.exists()


def test_surface_spec_round_trips_canonical_design():
    original = SyntheticGazeSurfaceSpec(
        base_spec=base_spec(),
        sampling_rates_hz=(30.0, 60.0),
        measurement_noise_sd_px=(0.0, 5.0),
        calibration_biases_px=((0.0, 0.0), (4.0, -3.0)),
        dropout_probabilities=(0.0, 0.05),
        random_states=(11, 12),
        max_conditions=64,
    )
    rebuilt = SyntheticGazeSurfaceSpec.from_dict(original.to_dict())
    assert rebuilt.to_dict() == original.to_dict()