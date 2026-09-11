from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import SchemaError
from gazeforge.quality_gating import (
    MotionQualityGateSpec,
    apply_accelerometer_quality_gate,
    apply_motion_quality_gate,
    build_motion_quality_certificate,
    derive_accelerometer_motion_index,
    freeze_motion_quality_certificate,
    quality_weight_from_motion,
    summarize_motion_quality,
    validate_motion_quality_certificate,
)


def motion_frame():
    return pd.DataFrame(
        {
            "participant_id": ["P1"] * 6,
            "trial_id": ["T1"] * 6,
            "timestamp_ms": [0.0, 100.0, 200.0, 300.0, 400.0, 500.0],
            "acc_x": [0.0, 0.0, 0.0, 1.0, 1.0, 1.0],
            "acc_y": [0.0] * 6,
            "acc_z": [1.0] * 6,
            "pupil": [3.0, 3.1, 3.2, 3.3, 3.4, 3.5],
        },
        index=[10, 11, 12, 13, 14, 15],
    )


def test_constant_acceleration_keeps_first_transition_unknown_then_zero():
    data = motion_frame()
    data["acc_x"] = 0.0
    out = derive_accelerometer_motion_index(data, smoothing_window_ms=200.0)
    assert np.isnan(out.iloc[0]["motion_jerk"])
    assert np.isnan(out.iloc[0]["motion_index"])
    assert (out.iloc[1:]["motion_jerk"] == 0.0).all()
    assert (out.iloc[1:]["motion_index"] == 0.0).all()
    assert out.index.equals(data.index)


def test_accelerometer_step_produces_positive_jerk_and_smoothed_motion():
    out = derive_accelerometer_motion_index(motion_frame(), smoothing_window_ms=200.0)
    assert out.loc[13, "motion_jerk"] == pytest.approx(10.0)
    assert out.loc[13, "motion_index"] > 0
    assert out.loc[14, "motion_index"] > 0
    assert out.loc[15, "motion_index"] >= 0


def test_motion_derivative_resets_at_group_boundary():
    first = motion_frame().iloc[:3].copy()
    second = motion_frame().iloc[:3].copy()
    second["participant_id"] = "P2"
    second["acc_x"] = 100.0
    combined = pd.concat([first, second], ignore_index=True)
    out = derive_accelerometer_motion_index(combined, smoothing_window_ms=100.0)
    assert np.isnan(out.loc[0, "motion_jerk"])
    assert np.isnan(out.loc[0, "motion_index"])
    assert np.isnan(out.loc[3, "motion_jerk"])
    assert np.isnan(out.loc[3, "motion_index"])


def test_group_boundary_unknown_propagates_to_quality_gate():
    spec = MotionQualityGateSpec(clean_threshold=2.0, severe_threshold=12.0)
    out = apply_accelerometer_quality_gate(
        motion_frame(),
        spec=spec,
        modality="pupil",
        signal_cols=("pupil",),
    )
    assert out.iloc[0]["quality_state"] == "motion_unknown"
    assert np.isnan(out.iloc[0]["quality_weight"])


def test_missing_acceleration_stays_unknown_instead_of_clean():
    data = motion_frame()
    data.loc[12, "acc_x"] = np.nan
    out = derive_accelerometer_motion_index(data, smoothing_window_ms=200.0)
    assert np.isnan(out.loc[12, "motion_jerk"])
    assert np.isnan(out.loc[12, "motion_index"])
    assert np.isnan(out.loc[13, "motion_jerk"])
    assert np.isnan(out.loc[13, "motion_index"])


@pytest.mark.parametrize(
    "timestamps",
    [
        [0.0, 100.0, 100.0, 300.0, 400.0, 500.0],
        [0.0, 100.0, 50.0, 300.0, 400.0, 500.0],
    ],
)
def test_nonincreasing_motion_timestamps_fail_closed(timestamps):
    data = motion_frame()
    data["timestamp_ms"] = timestamps
    with pytest.raises(SchemaError, match="strictly increasing"):
        derive_accelerometer_motion_index(data)


def test_missing_motion_timestamp_fails_closed():
    data = motion_frame()
    data.loc[12, "timestamp_ms"] = np.nan
    with pytest.raises(SchemaError, match="finite"):
        derive_accelerometer_motion_index(data)


def test_motion_index_requires_distinct_axes_and_output_names():
    data = motion_frame()
    with pytest.raises(ValueError, match="distinct"):
        derive_accelerometer_motion_index(data, accel_cols=("acc_x", "acc_x"))
    with pytest.raises(ValueError, match="distinct"):
        derive_accelerometer_motion_index(data, jerk_col="motion", motion_index_col="motion")


def test_motion_index_missing_columns_fail_closed():
    with pytest.raises(SchemaError, match="Missing columns"):
        derive_accelerometer_motion_index(motion_frame().drop(columns="acc_z"))


def test_motion_index_refuses_silent_output_overwrite():
    data = motion_frame()
    data["motion_index"] = 0.0
    with pytest.raises(SchemaError, match="already exist"):
        derive_accelerometer_motion_index(data)
    out = derive_accelerometer_motion_index(data, overwrite=True)
    assert "motion_index" in out


def test_overwrite_never_allows_motion_outputs_to_replace_source_columns():
    data = motion_frame()
    with pytest.raises(SchemaError, match="protected input"):
        derive_accelerometer_motion_index(data, jerk_col="acc_x", overwrite=True)
    with pytest.raises(SchemaError, match="protected input"):
        derive_accelerometer_motion_index(data, motion_index_col="timestamp_ms", overwrite=True)


def test_quality_weight_mapping_is_bounded_monotone_and_exact_at_thresholds():
    values = pd.Series([0.0, 1.0, 2.5, 4.0, 8.0, np.nan])
    weights = quality_weight_from_motion(
        values,
        clean_threshold=1.0,
        severe_threshold=4.0,
        minimum_weight=0.10,
    )
    assert weights.iloc[0] == pytest.approx(1.0)
    assert weights.iloc[1] == pytest.approx(1.0)
    assert 0.10 < weights.iloc[2] < 1.0
    assert weights.iloc[3] == pytest.approx(0.10)
    assert weights.iloc[4] == pytest.approx(0.10)
    assert np.isnan(weights.iloc[5])
    finite = weights.dropna().to_numpy()
    assert np.all(np.diff(finite) <= 1e-12)
    assert np.all((finite >= 0.0) & (finite <= 1.0))


def test_negative_motion_index_is_rejected():
    with pytest.raises(ValueError, match="non-negative"):
        quality_weight_from_motion(
            [0.0, -0.1], clean_threshold=1.0, severe_threshold=4.0
        )


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"clean_threshold": -1.0, "severe_threshold": 4.0}, "clean_threshold"),
        ({"clean_threshold": 2.0, "severe_threshold": 2.0}, "severe_threshold"),
        (
            {"clean_threshold": 1.0, "severe_threshold": 4.0, "minimum_weight": -0.1},
            "minimum_weight",
        ),
        (
            {"clean_threshold": 1.0, "severe_threshold": 4.0, "minimum_weight": 1.1},
            "minimum_weight",
        ),
        (
            {"clean_threshold": 1.0, "severe_threshold": 4.0, "smoothing_window_ms": 0},
            "smoothing_window_ms",
        ),
        (
            {"clean_threshold": 1.0, "severe_threshold": 4.0, "threshold_basis": ""},
            "threshold_basis",
        ),
    ],
)
def test_gate_spec_rejects_invalid_settings(kwargs, message):
    with pytest.raises(ValueError, match=message):
        MotionQualityGateSpec(**kwargs)


def test_gate_spec_canonicalizes_numeric_inputs_and_threshold_basis():
    spec = MotionQualityGateSpec(
        clean_threshold="1.0",
        severe_threshold="4.0",
        minimum_weight="0.2",
        smoothing_window_ms="250",
        threshold_basis="  pilot calibration  ",
    )
    assert spec.clean_threshold == pytest.approx(1.0)
    assert spec.severe_threshold == pytest.approx(4.0)
    assert spec.minimum_weight == pytest.approx(0.2)
    assert spec.smoothing_window_ms == pytest.approx(250.0)
    assert spec.threshold_basis == "pilot calibration"
    assert quality_weight_from_motion(
        [0.0, 2.5, 5.0],
        clean_threshold=spec.clean_threshold,
        severe_threshold=spec.severe_threshold,
        minimum_weight=spec.minimum_weight,
    ).tolist() == pytest.approx([1.0, 0.6, 0.2])


def test_apply_gate_classifies_clean_downweighted_severe_and_unknown():
    data = pd.DataFrame({"motion_index": [0.5, 2.5, 5.0, np.nan], "pupil": [1, 2, 3, 4]})
    spec = MotionQualityGateSpec(clean_threshold=1.0, severe_threshold=4.0)
    out = apply_motion_quality_gate(
        data, spec=spec, modality="pupil", signal_cols=("pupil",)
    )
    assert out["quality_state"].tolist() == [
        "clean",
        "downweighted",
        "severe",
        "motion_unknown",
    ]
    assert out.loc[0, "quality_weight"] == pytest.approx(1.0)
    assert 0.10 < out.loc[1, "quality_weight"] < 1.0
    assert out.loc[2, "quality_weight"] == pytest.approx(0.10)
    assert np.isnan(out.loc[3, "quality_weight"])


def test_signal_missing_is_zero_weight_even_when_motion_is_clean():
    data = pd.DataFrame({"motion_index": [0.0, 0.0], "pupil": [3.0, np.nan]})
    spec = MotionQualityGateSpec(clean_threshold=1.0, severe_threshold=4.0)
    out = apply_motion_quality_gate(
        data, spec=spec, modality="pupil", signal_cols=("pupil",)
    )
    assert out.loc[0, "quality_state"] == "clean"
    assert out.loc[0, "quality_weight"] == pytest.approx(1.0)
    assert out.loc[1, "quality_state"] == "signal_missing"
    assert out.loc[1, "quality_weight"] == pytest.approx(0.0)


def test_gate_preserves_rows_index_and_signal_values():
    data = motion_frame()
    before = data["pupil"].copy()
    spec = MotionQualityGateSpec(clean_threshold=2.0, severe_threshold=12.0)
    out = apply_accelerometer_quality_gate(
        data,
        spec=spec,
        modality="pupil",
        signal_cols=("pupil",),
    )
    assert len(out) == len(data)
    assert out.index.equals(data.index)
    pd.testing.assert_series_equal(out["pupil"], before)
    assert out["quality_modality"].eq("pupil").all()


def test_gate_refuses_silent_output_overwrite():
    data = pd.DataFrame({"motion_index": [0.0], "quality_weight": [0.5]})
    spec = MotionQualityGateSpec(clean_threshold=1.0, severe_threshold=4.0)
    with pytest.raises(SchemaError, match="already exist"):
        apply_motion_quality_gate(data, spec=spec, modality="eda")


def test_gate_outputs_must_be_distinct_even_when_overwrite_is_requested():
    data = pd.DataFrame({"motion_index": [0.0], "pupil": [3.0]})
    spec = MotionQualityGateSpec(clean_threshold=1.0, severe_threshold=4.0)
    with pytest.raises(ValueError, match="distinct"):
        apply_motion_quality_gate(
            data,
            spec=spec,
            modality="pupil",
            signal_cols=("pupil",),
            weight_col="quality",
            state_col="quality",
            overwrite=True,
        )


def test_overwrite_never_allows_quality_outputs_to_replace_signal_or_motion_inputs():
    data = pd.DataFrame({"motion_index": [0.0], "pupil": [3.0]})
    spec = MotionQualityGateSpec(clean_threshold=1.0, severe_threshold=4.0)
    with pytest.raises(SchemaError, match="protected input"):
        apply_motion_quality_gate(
            data,
            spec=spec,
            modality="pupil",
            signal_cols=("pupil",),
            weight_col="pupil",
            overwrite=True,
        )
    with pytest.raises(SchemaError, match="protected input"):
        apply_motion_quality_gate(
            data,
            spec=spec,
            modality="pupil",
            state_col="motion_index",
            overwrite=True,
        )


def test_combined_gate_protects_all_source_columns_and_cross_stage_output_names():
    data = motion_frame()
    spec = MotionQualityGateSpec(clean_threshold=2.0, severe_threshold=12.0)
    with pytest.raises(SchemaError, match="protected input"):
        apply_accelerometer_quality_gate(
            data,
            spec=spec,
            modality="pupil",
            signal_cols=("pupil",),
            weight_col="acc_x",
            overwrite=True,
        )
    with pytest.raises(ValueError, match="distinct"):
        apply_accelerometer_quality_gate(
            data,
            spec=spec,
            modality="pupil",
            signal_cols=("pupil",),
            jerk_col="derived",
            weight_col="derived",
            overwrite=True,
        )


def test_summary_reports_effective_weight_and_state_fractions():
    data = pd.DataFrame(
        {
            "participant_id": ["P1"] * 4,
            "trial_id": ["T1"] * 4,
            "quality_modality": ["pupil"] * 4,
            "quality_weight": [1.0, 0.5, 0.1, np.nan],
            "quality_state": ["clean", "downweighted", "severe", "motion_unknown"],
        }
    )
    summary = summarize_motion_quality(data)
    assert len(summary) == 1
    row = summary.iloc[0]
    assert row["n_samples"] == 4
    assert row["n_known_weights"] == 3
    assert row["n_unknown_weights"] == 1
    assert row["effective_weight_sum"] == pytest.approx(1.6)
    assert row["clean_fraction"] == pytest.approx(0.25)
    assert row["motion_unknown_fraction"] == pytest.approx(0.25)


def test_summary_rejects_invalid_weights_and_unknown_states():
    base = pd.DataFrame(
        {
            "participant_id": ["P1"],
            "trial_id": ["T1"],
            "quality_modality": ["pupil"],
            "quality_weight": [1.2],
            "quality_state": ["clean"],
        }
    )
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        summarize_motion_quality(base)
    changed = base.copy()
    changed["quality_weight"] = 0.5
    changed["quality_state"] = "invented"
    with pytest.raises(ValueError, match="Unknown motion-quality states"):
        summarize_motion_quality(changed)


def test_certificate_is_deterministic_replayable_and_privacy_preserving():
    data = motion_frame()
    spec = MotionQualityGateSpec(
        clean_threshold=2.0,
        severe_threshold=12.0,
        threshold_basis="device-specific pilot threshold",
    )
    first = build_motion_quality_certificate(
        data, spec=spec, modality="pupil", signal_cols=("pupil",)
    )
    second = build_motion_quality_certificate(
        data, spec=spec, modality="pupil", signal_cols=("pupil",)
    )
    assert first == second
    assert first["claim_boundary"]["reliability_weighting_only"] is True
    assert first["claim_boundary"]["removes_samples"] is False
    assert first["claim_boundary"]["corrects_motion_artifacts"] is False
    assert first["claim_boundary"]["thresholds_empirically_validated"] is False
    assert first["summary"]["n_rows"] == len(data)
    assert '"P1"' not in str(first)
    assert validate_motion_quality_certificate(first, data)


def test_certificate_normalizes_modality_and_spec_metadata():
    data = motion_frame()
    spec = MotionQualityGateSpec(
        clean_threshold="2",
        severe_threshold="12",
        threshold_basis="  pilot  ",
    )
    certificate = build_motion_quality_certificate(
        data,
        spec=spec,
        modality="  pupil  ",
        signal_cols=("pupil",),
    )
    assert certificate["spec"]["clean_threshold"] == pytest.approx(2.0)
    assert certificate["spec"]["threshold_basis"] == "pilot"
    assert certificate["gate_config"]["modality"] == "pupil"
    assert validate_motion_quality_certificate(certificate, data)


def test_resigned_claim_promotion_cannot_replay():
    data = motion_frame()
    spec = MotionQualityGateSpec(clean_threshold=2.0, severe_threshold=12.0)
    certificate = build_motion_quality_certificate(data, spec=spec, modality="pupil")
    promoted = dict(certificate)
    promoted["claim_boundary"] = dict(certificate["claim_boundary"])
    promoted["claim_boundary"]["corrects_motion_artifacts"] = True
    body = {k: v for k, v in promoted.items() if k != "certificate_fingerprint_sha256"}
    promoted["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    with pytest.raises(ValueError, match="claim boundary"):
        validate_motion_quality_certificate(promoted, data)


def test_resigned_summary_or_output_promotion_cannot_replay():
    data = motion_frame()
    spec = MotionQualityGateSpec(clean_threshold=2.0, severe_threshold=12.0)
    certificate = build_motion_quality_certificate(data, spec=spec, modality="pupil")
    changed = dict(certificate)
    changed["summary"] = dict(certificate["summary"])
    changed["summary"]["mean_quality_weight"] = 1.0
    body = {k: v for k, v in changed.items() if k != "certificate_fingerprint_sha256"}
    changed["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    with pytest.raises(ValueError, match="does not replay"):
        validate_motion_quality_certificate(changed, data)


def test_data_mutation_invalidates_motion_quality_certificate():
    data = motion_frame()
    spec = MotionQualityGateSpec(clean_threshold=2.0, severe_threshold=12.0)
    certificate = build_motion_quality_certificate(data, spec=spec, modality="pupil")
    changed = data.copy()
    changed.loc[13, "acc_x"] = 2.0
    with pytest.raises(ValueError, match="does not replay"):
        validate_motion_quality_certificate(certificate, changed)


def test_freeze_requires_exact_replay_and_protects_existing_file(tmp_path: Path):
    data = motion_frame()
    spec = MotionQualityGateSpec(clean_threshold=2.0, severe_threshold=12.0)
    certificate = build_motion_quality_certificate(data, spec=spec, modality="pupil")
    target = tmp_path / "motion-quality.json"
    written = freeze_motion_quality_certificate(certificate, target, data=data)
    assert written == target
    assert target.exists()
    with pytest.raises(FileExistsError):
        freeze_motion_quality_certificate(certificate, target, data=data)


def test_promoted_certificate_is_rejected_before_persistence(tmp_path: Path):
    data = motion_frame()
    spec = MotionQualityGateSpec(clean_threshold=2.0, severe_threshold=12.0)
    certificate = build_motion_quality_certificate(data, spec=spec, modality="pupil")
    promoted = dict(certificate)
    promoted["claim_boundary"] = dict(certificate["claim_boundary"])
    promoted["claim_boundary"]["establishes_sensor_validity"] = True
    body = {k: v for k, v in promoted.items() if k != "certificate_fingerprint_sha256"}
    promoted["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    target = tmp_path / "promoted.json"
    with pytest.raises(ValueError, match="claim boundary"):
        freeze_motion_quality_certificate(promoted, target, data=data)
    assert not target.exists()
