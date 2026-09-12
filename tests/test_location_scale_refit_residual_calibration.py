from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.correlated_location_random_slope_scale import (
    CorrelatedLocationRandomSlopeScaleSpec,
    fit_correlated_location_random_slope_scale,
)
from gazeforge.exceptions import SchemaError
from gazeforge.hierarchical_location_scale import (
    HierarchicalLocationScaleSpec,
    fit_hierarchical_location_scale,
)
from gazeforge.location_scale_refit_residual_calibration import (
    LocationScaleRefitResidualCalibrationSpec,
    build_location_scale_refit_residual_calibration_certificate,
    calibrate_location_scale_residuals_with_refits,
    validate_location_scale_refit_residual_calibration_certificate,
)


def _synthetic(seed: int = 41) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, float | str]] = []
    x_grid = np.linspace(-1.4, 1.4, 12)
    for group_index in range(16):
        location_effect = rng.normal(0.0, 0.35)
        scale_effect = rng.normal(0.0, 0.12)
        for x in x_grid:
            location = 0.70 + 0.45 * x + location_effect
            sigma = np.exp(-0.15 + 0.06 * x + scale_effect)
            rows.append(
                {
                    "participant_id": f"p{group_index:02d}",
                    "x": float(x),
                    "y": float(rng.normal(location, sigma)),
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def independent_fit():
    data = _synthetic()
    spec = HierarchicalLocationScaleSpec(
        outcome_col="y",
        group_col="participant_id",
        location_predictors=("x",),
        scale_predictors=("x",),
        quadrature_points=3,
        max_iter=450,
        tolerance=1e-6,
    )
    fitted = fit_hierarchical_location_scale(data, spec=spec)
    assert fitted.converged
    return data, fitted


def _refit_spec(seed: int = 811) -> LocationScaleRefitResidualCalibrationSpec:
    return LocationScaleRefitResidualCalibrationSpec(
        n_simulations=2,
        seed=seed,
        envelope_level=0.90,
        max_refit_rows=1_000,
    )


@pytest.fixture(scope="module")
def refit_calibration(independent_fit):
    data, fitted = independent_fit
    return calibrate_location_scale_residuals_with_refits(
        fitted,
        data,
        spec=_refit_spec(),
    )


def test_refit_calibration_is_deterministic_with_complete_lineage(
    independent_fit,
    refit_calibration,
):
    data, fitted = independent_fit
    repeated = calibrate_location_scale_residuals_with_refits(
        fitted,
        data,
        spec=_refit_spec(),
    )

    assert refit_calibration.model_family == "independent_location_scale"
    assert refit_calibration.model_fingerprint_sha256 == fitted.model_fingerprint_sha256
    assert refit_calibration.n_obs == len(data)
    assert refit_calibration.n_groups == data["participant_id"].nunique()
    assert len(refit_calibration.refit_ledger) == 2
    assert [row["simulation_index"] for row in refit_calibration.refit_ledger] == [0, 1]
    for row in refit_calibration.refit_ledger:
        assert len(row["model_fingerprint_sha256"]) == 64
        assert len(row["model_certificate_fingerprint_sha256"]) == 64
        assert len(row["standardized_residuals_fingerprint_sha256"]) == 64
    assert (
        refit_calibration.diagnostic_fingerprint_sha256
        == repeated.diagnostic_fingerprint_sha256
    )
    assert (
        refit_calibration.refit_ledger_fingerprint_sha256
        == repeated.refit_ledger_fingerprint_sha256
    )
    assert refit_calibration.refit_ledger == repeated.refit_ledger
    pd.testing.assert_frame_equal(refit_calibration.summary, repeated.summary)


def test_refit_certificate_roundtrip(refit_calibration):
    certificate = build_location_scale_refit_residual_calibration_certificate(
        refit_calibration
    )
    validate_location_scale_refit_residual_calibration_certificate(certificate)
    assert certificate["diagnostic"]["model_family"] == "independent_location_scale"
    assert len(certificate["refit_ledger"]) == refit_calibration.spec.n_simulations


def test_refit_calibration_requires_exact_fitting_input(independent_fit):
    data, fitted = independent_fit
    changed = data.copy()
    changed.loc[0, "y"] += 0.01
    with pytest.raises(SchemaError, match="exact fitted modelling input"):
        calibrate_location_scale_residuals_with_refits(
            fitted,
            changed,
            spec=_refit_spec(),
        )


def test_refit_resource_budget_fails_before_refitting(independent_fit):
    data, fitted = independent_fit
    spec = LocationScaleRefitResidualCalibrationSpec(
        n_simulations=2,
        max_refit_rows=len(data),
    )
    with pytest.raises(SchemaError, match="resource budget exceeded"):
        calibrate_location_scale_residuals_with_refits(fitted, data, spec=spec)


def test_any_failed_refit_aborts_instead_of_being_dropped(
    independent_fit,
    monkeypatch,
):
    data, fitted = independent_fit

    def fail_refit(*args, **kwargs):
        raise RuntimeError("synthetic refit failure")

    monkeypatch.setattr(
        "gazeforge.location_scale_refit_residual_calibration._fit_function_for_result",
        lambda result: fail_refit,
    )
    with pytest.raises(
        SchemaError,
        match="simulation 0 did not produce a converged certifiable refit",
    ):
        calibrate_location_scale_residuals_with_refits(
            fitted,
            data,
            spec=_refit_spec(),
        )


def test_resigned_claim_promotion_is_rejected(refit_calibration):
    certificate = build_location_scale_refit_residual_calibration_certificate(
        refit_calibration
    )
    promoted = deepcopy(certificate)
    promoted["claim_boundary"]["parameter_estimation_uncertainty_quantified"] = True
    body = {
        key: value
        for key, value in promoted.items()
        if key != "certificate_fingerprint_sha256"
    }
    promoted["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    with pytest.raises(SchemaError, match="claim boundary"):
        validate_location_scale_refit_residual_calibration_certificate(promoted)


def test_resigned_unknown_model_family_is_rejected(refit_calibration):
    certificate = build_location_scale_refit_residual_calibration_certificate(
        refit_calibration
    )
    attacked = deepcopy(certificate)
    attacked["diagnostic"]["model_family"] = "population_random_effect_bootstrap"
    attacked["diagnostic_fingerprint_sha256"] = benchmark_fingerprint(
        attacked["diagnostic"]
    )
    body = {
        key: value
        for key, value in attacked.items()
        if key != "certificate_fingerprint_sha256"
    }
    attacked["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    with pytest.raises(SchemaError, match="model family is invalid"):
        validate_location_scale_refit_residual_calibration_certificate(attacked)


def test_noncanonical_refit_ledger_schema_is_rejected(refit_calibration):
    certificate = build_location_scale_refit_residual_calibration_certificate(
        refit_calibration
    )
    attacked = deepcopy(certificate)
    attacked["refit_ledger"][0]["accepted"] = True
    attacked["diagnostic"]["refit_ledger_fingerprint_sha256"] = benchmark_fingerprint(
        attacked["refit_ledger"]
    )
    attacked["diagnostic_fingerprint_sha256"] = benchmark_fingerprint(
        attacked["diagnostic"]
    )
    body = {
        key: value
        for key, value in attacked.items()
        if key != "certificate_fingerprint_sha256"
    }
    attacked["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    with pytest.raises(SchemaError, match="noncanonical schema"):
        validate_location_scale_refit_residual_calibration_certificate(attacked)


def test_invalid_refit_specs_fail_closed():
    with pytest.raises(ValueError, match="2 through 10000"):
        LocationScaleRefitResidualCalibrationSpec(n_simulations=1)
    with pytest.raises(ValueError, match="2 through 10000"):
        LocationScaleRefitResidualCalibrationSpec(n_simulations=10_001)
    with pytest.raises(ValueError, match="between 0.5 and 1.0"):
        LocationScaleRefitResidualCalibrationSpec(envelope_level=1.0)
    with pytest.raises(ValueError, match="non-negative integer"):
        LocationScaleRefitResidualCalibrationSpec(seed=-1)
    with pytest.raises(ValueError, match="positive integer"):
        LocationScaleRefitResidualCalibrationSpec(max_refit_rows=0)


def _correlated_slope_synthetic(seed: int = 419) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, float | str]] = []
    x_grid = np.linspace(-1.5, 1.5, 12)
    rho = 0.25
    for group_index in range(24):
        z0, z1 = rng.normal(size=2)
        b0 = 0.45 * z0
        b1 = 0.24 * (rho * z0 + np.sqrt(1.0 - rho**2) * z1)
        c = rng.normal(0.0, 0.14)
        for x in x_grid:
            sigma = np.exp(np.log(0.62) + 0.05 * x + c)
            mean = 1.30 + 0.75 * x + b0 + b1 * x
            rows.append(
                {
                    "participant_id": f"P{group_index:02d}",
                    "condition": float(x),
                    "outcome": float(rng.normal(mean, sigma)),
                }
            )
    return pd.DataFrame(rows)


def test_refit_calibration_supports_correlated_random_slope_family():
    data = _correlated_slope_synthetic()
    model_spec = CorrelatedLocationRandomSlopeScaleSpec(
        outcome_col="outcome",
        group_col="participant_id",
        random_slope_predictor="condition",
        location_predictors=("condition",),
        scale_predictors=("condition",),
        quadrature_points=3,
        min_group_size=4,
        max_iter=500,
        tolerance=1e-6,
    )
    fitted = fit_correlated_location_random_slope_scale(data, spec=model_spec)
    assert fitted.converged
    calibration = calibrate_location_scale_residuals_with_refits(
        fitted,
        data,
        spec=LocationScaleRefitResidualCalibrationSpec(
            n_simulations=2,
            seed=313,
            envelope_level=0.90,
            max_refit_rows=1_000,
        ),
    )
    assert calibration.model_family == "correlated_location_random_slope_scale"
    assert len(calibration.refit_ledger) == 2
    assert (
        calibration.base_model_certificate_fingerprint_sha256
        != calibration.model_fingerprint_sha256
    )
    certificate = build_location_scale_refit_residual_calibration_certificate(
        calibration
    )
    validate_location_scale_refit_residual_calibration_certificate(certificate)
    assert (
        certificate["diagnostic"]["model_family"]
        == "correlated_location_random_slope_scale"
    )
