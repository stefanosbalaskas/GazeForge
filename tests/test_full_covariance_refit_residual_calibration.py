from __future__ import annotations

from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import SchemaError
from gazeforge.full_covariance_location_random_slope_scale import (
    FullCovarianceLocationRandomSlopeScaleSpec,
    build_full_covariance_location_random_slope_scale_certificate,
    fit_full_covariance_location_random_slope_scale,
)
from gazeforge.location_scale_refit_residual_calibration import (
    LocationScaleRefitResidualCalibrationSpec,
    build_location_scale_refit_residual_calibration_certificate,
    calibrate_location_scale_residuals_with_refits,
    validate_location_scale_refit_residual_calibration_certificate,
)


def _synthetic(seed: int = 911) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    tau0 = 0.52
    tau1 = 0.30
    tau_scale = 0.24
    correlation = np.array(
        [
            [1.0, 0.55, 0.45],
            [0.55, 1.0, 0.35],
            [0.45, 0.35, 1.0],
        ]
    )
    covariance = np.diag([tau0, tau1, tau_scale]) @ correlation @ np.diag(
        [tau0, tau1, tau_scale]
    )
    effects = rng.multivariate_normal(np.zeros(3), covariance, size=20)
    x_grid = np.linspace(-1.35, 1.35, 9)
    rows: list[dict[str, float | str]] = []
    for group_index, (b0, b1, c) in enumerate(effects):
        for x in x_grid:
            log_sigma = -0.55 + 0.08 * x + c
            mean = 1.35 + 0.72 * x + b0 + b1 * x
            rows.append(
                {
                    "participant_id": f"P{group_index:02d}",
                    "condition": float(x),
                    "outcome": float(rng.normal(mean, np.exp(log_sigma))),
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def full_covariance_fit():
    data = _synthetic()
    model_spec = FullCovarianceLocationRandomSlopeScaleSpec(
        outcome_col="outcome",
        group_col="participant_id",
        random_slope_predictor="condition",
        location_predictors=("condition",),
        scale_predictors=("condition",),
        quadrature_points=3,
        min_group_size=4,
        max_iter=500,
        tolerance=1e-5,
    )
    fitted = fit_full_covariance_location_random_slope_scale(data, spec=model_spec)
    assert fitted.converged
    return data, fitted


def _refit_spec(seed: int = 2601) -> LocationScaleRefitResidualCalibrationSpec:
    return LocationScaleRefitResidualCalibrationSpec(
        n_simulations=2,
        seed=seed,
        envelope_level=0.90,
        max_refit_rows=1_000,
    )


@pytest.fixture(scope="module")
def full_covariance_refit_calibration(full_covariance_fit):
    data, fitted = full_covariance_fit
    return calibrate_location_scale_residuals_with_refits(
        fitted,
        data,
        spec=_refit_spec(),
    )


def test_full_covariance_refit_calibration_is_certifiable_with_complete_lineage(
    full_covariance_fit,
    full_covariance_refit_calibration,
) -> None:
    data, fitted = full_covariance_fit
    calibration = full_covariance_refit_calibration
    assert calibration.model_family == "full_covariance_location_random_slope_scale"
    assert calibration.model_fingerprint_sha256 == fitted.model_fingerprint_sha256
    assert calibration.n_obs == len(data)
    assert calibration.n_groups == data["participant_id"].nunique()
    assert len(calibration.refit_ledger) == 2
    assert [row["simulation_index"] for row in calibration.refit_ledger] == [0, 1]
    for row in calibration.refit_ledger:
        assert len(row["model_fingerprint_sha256"]) == 64
        assert len(row["model_certificate_fingerprint_sha256"]) == 64
        assert len(row["standardized_residuals_fingerprint_sha256"]) == 64

    base_certificate = build_full_covariance_location_random_slope_scale_certificate(fitted)
    assert (
        calibration.base_model_certificate_fingerprint_sha256
        == base_certificate["certificate_fingerprint_sha256"]
    )
    certificate = build_location_scale_refit_residual_calibration_certificate(calibration)
    validate_location_scale_refit_residual_calibration_certificate(certificate)
    assert (
        certificate["diagnostic"]["model_family"]
        == "full_covariance_location_random_slope_scale"
    )


def test_full_covariance_refit_calibration_is_deterministic(
    full_covariance_fit,
    full_covariance_refit_calibration,
) -> None:
    data, fitted = full_covariance_fit
    repeated = calibrate_location_scale_residuals_with_refits(
        fitted,
        data,
        spec=_refit_spec(),
    )
    calibration = full_covariance_refit_calibration
    assert repeated.diagnostic_fingerprint_sha256 == calibration.diagnostic_fingerprint_sha256
    assert repeated.refit_ledger_fingerprint_sha256 == calibration.refit_ledger_fingerprint_sha256
    assert repeated.refit_ledger == calibration.refit_ledger
    pd.testing.assert_frame_equal(repeated.summary, calibration.summary)


def test_full_covariance_refit_calibration_requires_exact_fitted_input(
    full_covariance_fit,
) -> None:
    data, fitted = full_covariance_fit
    changed = data.copy()
    changed.loc[0, "outcome"] += 0.01
    with pytest.raises(SchemaError, match="exact fitted modelling input"):
        calibrate_location_scale_residuals_with_refits(
            fitted,
            changed,
            spec=_refit_spec(seed=2602),
        )


def test_full_covariance_refit_certificate_rejects_resigned_family_tamper(
    full_covariance_refit_calibration,
) -> None:
    certificate = build_location_scale_refit_residual_calibration_certificate(
        full_covariance_refit_calibration
    )
    attacked = deepcopy(certificate)
    attacked["diagnostic"]["model_family"] = "invented_full_covariance_refit_family"
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
