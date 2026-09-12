from copy import deepcopy
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import SchemaError
from gazeforge.location_random_slope_scale import (
    LocationRandomSlopeScaleSpec,
    build_location_random_slope_scale_certificate,
    fit_location_random_slope_scale,
    validate_location_random_slope_scale_certificate,
)
from gazeforge.location_scale_residual_calibration import (
    LocationScaleResidualCalibrationSpec,
    build_location_scale_residual_calibration_certificate,
    calibrate_location_scale_residuals,
    validate_location_scale_residual_calibration_certificate,
)


def _synthetic(seed: int = 944) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, float | str]] = []
    x_grid = np.linspace(-1.0, 1.0, 8)
    for group_index in range(8):
        b0 = rng.normal(0.0, 0.40)
        b1 = rng.normal(0.0, 0.45)
        c = rng.normal(0.0, 0.30)
        for x in x_grid:
            sigma = np.exp(-0.25 + 0.10 * x + c)
            mean = 1.8 + 0.85 * x + b0 + b1 * x
            rows.append(
                {
                    "participant_id": f"P{group_index:02d}",
                    "condition": float(x),
                    "outcome": float(rng.normal(mean, sigma)),
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def random_slope_fit():
    data = _synthetic()
    spec = LocationRandomSlopeScaleSpec(
        outcome_col="outcome",
        group_col="participant_id",
        random_slope_predictor="condition",
        location_predictors=("condition",),
        scale_predictors=("condition",),
        quadrature_points=3,
        min_group_size=4,
        max_iter=300,
    )
    result = fit_location_random_slope_scale(data, spec=spec)
    assert result.converged
    return data, result


def _calibration_spec(seed: int = 511):
    return LocationScaleResidualCalibrationSpec(
        n_simulations=50,
        seed=seed,
        envelope_level=0.90,
        max_simulated_residual_draws=10_000,
    )


def test_random_slope_family_calibrates_deterministically_with_base_lineage(
    random_slope_fit,
):
    data, fitted = random_slope_fit
    base_certificate = build_location_random_slope_scale_certificate(fitted)
    validate_location_random_slope_scale_certificate(base_certificate)

    first = calibrate_location_scale_residuals(
        fitted, data, spec=_calibration_spec()
    )
    second = calibrate_location_scale_residuals(
        fitted, data, spec=_calibration_spec()
    )

    assert first.model_family == "location_random_slope_scale"
    assert first.model_fingerprint_sha256 == fitted.model_fingerprint_sha256
    assert (
        first.base_model_certificate_fingerprint_sha256
        == base_certificate["certificate_fingerprint_sha256"]
    )
    assert first.diagnostic_fingerprint_sha256 == second.diagnostic_fingerprint_sha256
    pd.testing.assert_frame_equal(first.summary, second.summary)

    certificate = build_location_scale_residual_calibration_certificate(first)
    assert certificate["diagnostic"]["model_family"] == "location_random_slope_scale"
    validate_location_scale_residual_calibration_certificate(certificate)


def test_random_slope_calibration_requires_exact_fitting_input(random_slope_fit):
    data, fitted = random_slope_fit
    changed = data.copy()
    changed.loc[0, "condition"] += 0.01
    with pytest.raises(SchemaError, match="exact fitted modelling input"):
        calibrate_location_scale_residuals(
            fitted, changed, spec=_calibration_spec()
        )


def test_random_slope_calibration_rejects_noncertifiable_base_fit(random_slope_fit):
    data, fitted = random_slope_fit
    nonconverged = replace(fitted, converged=False)
    with pytest.raises(
        SchemaError,
        match="Only converged location random-slope scale fits are certifiable",
    ):
        calibrate_location_scale_residuals(
            nonconverged, data, spec=_calibration_spec()
        )


def test_resigned_unknown_model_family_still_fails_closed(random_slope_fit):
    data, fitted = random_slope_fit
    result = calibrate_location_scale_residuals(
        fitted, data, spec=_calibration_spec()
    )
    certificate = build_location_scale_residual_calibration_certificate(result)
    attacked = deepcopy(certificate)
    attacked["diagnostic"]["model_family"] = "unrestricted_random_effect_covariance"
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
        validate_location_scale_residual_calibration_certificate(attacked)
