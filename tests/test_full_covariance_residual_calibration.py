from __future__ import annotations

import copy

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
from gazeforge.location_scale_hierarchical_bootstrap import (
    LocationScaleHierarchicalBootstrapSpec,
    bootstrap_location_scale_hierarchy,
)
from gazeforge.location_scale_refit_residual_calibration import (
    LocationScaleRefitResidualCalibrationSpec,
    calibrate_location_scale_residuals_with_refits,
)
from gazeforge.location_scale_residual_calibration import (
    LocationScaleResidualCalibrationSpec,
    build_location_scale_residual_calibration_certificate,
    calibrate_location_scale_residuals,
    validate_location_scale_residual_calibration_certificate,
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
        for trial_index, x in enumerate(x_grid):
            log_sigma = -0.55 + 0.08 * x + c
            mean = 1.35 + 0.72 * x + b0 + b1 * x
            rows.append(
                {
                    "participant_id": f"P{group_index:02d}",
                    "trial_index": float(trial_index),
                    "condition": float(x),
                    "outcome": float(rng.normal(mean, np.exp(log_sigma))),
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def full_covariance_fit():
    data = _synthetic()
    spec = FullCovarianceLocationRandomSlopeScaleSpec(
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
    return data, fit_full_covariance_location_random_slope_scale(data, spec=spec)


def _calibration_spec(seed: int = 1901) -> LocationScaleResidualCalibrationSpec:
    return LocationScaleResidualCalibrationSpec(
        n_simulations=60,
        seed=seed,
        envelope_level=0.90,
        max_simulated_residual_draws=50_000,
    )


def test_full_covariance_fixed_fit_residual_calibration_is_certifiable_and_deterministic(
    full_covariance_fit,
) -> None:
    data, fitted = full_covariance_fit
    first = calibrate_location_scale_residuals(
        fitted,
        data,
        spec=_calibration_spec(),
    )
    second = calibrate_location_scale_residuals(
        fitted,
        data,
        spec=_calibration_spec(),
    )

    assert first.model_family == "full_covariance_location_random_slope_scale"
    assert first.model_fingerprint_sha256 == fitted.model_fingerprint_sha256
    assert first.n_obs == len(data)
    assert first.n_groups == data["participant_id"].nunique()
    assert first.diagnostic_fingerprint_sha256 == second.diagnostic_fingerprint_sha256
    pd.testing.assert_frame_equal(first.summary, second.summary)

    base_certificate = build_full_covariance_location_random_slope_scale_certificate(fitted)
    assert (
        first.base_model_certificate_fingerprint_sha256
        == base_certificate["certificate_fingerprint_sha256"]
    )
    certificate = build_location_scale_residual_calibration_certificate(first)
    validate_location_scale_residual_calibration_certificate(certificate)


def test_full_covariance_residual_calibration_requires_exact_fitted_input(
    full_covariance_fit,
) -> None:
    data, fitted = full_covariance_fit
    changed = data.copy()
    changed.loc[0, "outcome"] += 0.01
    with pytest.raises(SchemaError, match="exact fitted modelling input"):
        calibrate_location_scale_residuals(
            fitted,
            changed,
            spec=_calibration_spec(seed=1902),
        )


def test_residual_certificate_rejects_resigned_full_covariance_family_tamper(
    full_covariance_fit,
) -> None:
    data, fitted = full_covariance_fit
    result = calibrate_location_scale_residuals(
        fitted,
        data,
        spec=_calibration_spec(seed=1903),
    )
    certificate = build_location_scale_residual_calibration_certificate(result)
    tampered = copy.deepcopy(certificate)
    tampered["diagnostic"]["model_family"] = "invented_full_covariance_family"
    tampered["diagnostic_fingerprint_sha256"] = benchmark_fingerprint(
        tampered["diagnostic"]
    )
    body = {
        key: value
        for key, value in tampered.items()
        if key != "certificate_fingerprint_sha256"
    }
    tampered["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    with pytest.raises(SchemaError, match="model family is invalid"):
        validate_location_scale_residual_calibration_certificate(tampered)


def test_refit_and_bootstrap_adapters_still_reject_full_covariance_family(
    full_covariance_fit,
) -> None:
    data, fitted = full_covariance_fit
    with pytest.raises(TypeError):
        calibrate_location_scale_residuals_with_refits(
            fitted,
            data,
            spec=LocationScaleRefitResidualCalibrationSpec(
                n_simulations=2,
                seed=1904,
            ),
        )
    with pytest.raises(TypeError):
        bootstrap_location_scale_hierarchy(
            fitted,
            data,
            spec=LocationScaleHierarchicalBootstrapSpec(
                n_simulations=2,
                seed=1905,
            ),
        )
