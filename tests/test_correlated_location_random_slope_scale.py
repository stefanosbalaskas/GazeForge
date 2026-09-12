from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import gazeforge.correlated_location_random_slope_scale as correlated_slope_module
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.correlated_location_random_slope_scale import (
    CorrelatedLocationRandomSlopeScaleSpec,
    _latent_location_parameterization,
    build_correlated_location_random_slope_scale_certificate,
    correlated_location_random_slope_scale_diagnostics,
    fit_correlated_location_random_slope_scale,
    freeze_correlated_location_random_slope_scale_certificate,
    predict_correlated_location_random_slope_scale,
    validate_correlated_location_random_slope_scale_certificate,
)
from gazeforge.exceptions import SchemaError


def _synthetic(seed: int = 731) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, float | str]] = []
    x_grid = np.linspace(-1.25, 1.25, 10)
    latent = np.linspace(-1.7, 1.7, 12)
    for group_index, z in enumerate(latent):
        b0 = 0.48 * z + rng.normal(0.0, 0.08)
        b1 = 0.38 * z + rng.normal(0.0, 0.10)
        c = rng.normal(0.0, 0.22)
        for trial_index, x in enumerate(x_grid):
            sigma = np.exp(np.log(0.58) + 0.08 * x + c)
            mean = 1.7 + 0.85 * x + b0 + b1 * x
            rows.append(
                {
                    "participant_id": f"P{group_index:02d}",
                    "trial_index": float(trial_index),
                    "condition": float(x),
                    "outcome": float(rng.normal(mean, sigma)),
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def fitted() -> tuple[pd.DataFrame, object]:
    data = _synthetic()
    spec = CorrelatedLocationRandomSlopeScaleSpec(
        outcome_col="outcome",
        group_col="participant_id",
        random_slope_predictor="condition",
        location_predictors=("condition",),
        scale_predictors=("condition",),
        quadrature_points=3,
        min_group_size=4,
        max_iter=320,
        tolerance=1e-7,
    )
    return data, fit_correlated_location_random_slope_scale(data, spec=spec)


def _resign(certificate: dict) -> None:
    certificate["model_fingerprint_sha256"] = benchmark_fingerprint(certificate["model"])
    body = {
        key: value
        for key, value in certificate.items()
        if key != "certificate_fingerprint_sha256"
    }
    certificate["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)


def test_latent_parameterization_recovers_requested_location_covariance() -> None:
    tau0 = 0.70
    tau1 = 0.42
    rho = 0.58
    latent_tau0, delta = _latent_location_parameterization(tau0, tau1, rho)
    transform = np.array([[1.0, -delta], [0.0, 1.0]])
    latent_covariance = np.diag([latent_tau0**2, tau1**2])
    recovered = transform @ latent_covariance @ transform.T
    expected = np.array(
        [
            [tau0**2, rho * tau0 * tau1],
            [rho * tau0 * tau1, tau1**2],
        ]
    )
    assert recovered == pytest.approx(expected, abs=1e-12)


def test_location_covariance_family_is_closed_under_predictor_zero_point_shift() -> None:
    tau0 = 0.65
    tau1 = 0.35
    rho = -0.40
    covariance = np.array(
        [
            [tau0**2, rho * tau0 * tau1],
            [rho * tau0 * tau1, tau1**2],
        ]
    )
    shift = 2.75
    transform = np.array([[1.0, shift], [0.0, 1.0]])
    shifted = transform @ covariance @ transform.T
    shifted_tau0 = float(np.sqrt(shifted[0, 0]))
    shifted_tau1 = float(np.sqrt(shifted[1, 1]))
    shifted_rho = float(shifted[0, 1] / (shifted_tau0 * shifted_tau1))
    reconstructed = np.array(
        [
            [shifted_tau0**2, shifted_rho * shifted_tau0 * shifted_tau1],
            [shifted_rho * shifted_tau0 * shifted_tau1, shifted_tau1**2],
        ]
    )
    assert reconstructed == pytest.approx(shifted, abs=1e-12)
    assert abs(shifted_rho) < 1.0


def test_known_truth_fit_recovers_positive_intercept_slope_association(
    fitted: tuple[pd.DataFrame, object],
) -> None:
    _, result = fitted
    assert result.converged
    assert result.location_terms == ("Intercept", "condition")
    assert result.scale_terms == ("Intercept", "condition")
    assert result.location_coef[1] > 0.25
    assert result.tau_location_intercept > 0.05
    assert result.tau_location_slope > 0.05
    assert result.tau_scale > correlated_slope_module._MIN_RANDOM_EFFECT_SD
    assert result.rho_location_intercept_slope > 0.10
    assert result.random_effect_correlation() == result.rho_location_intercept_slope
    assert len(result.group_effects) == 12


def test_prediction_and_diagnostics_preserve_known_and_unseen_semantics(
    fitted: tuple[pd.DataFrame, object],
) -> None:
    data, result = fitted
    known = data.iloc[[0]].copy()
    conditional = predict_correlated_location_random_slope_scale(result, known)
    population = predict_correlated_location_random_slope_scale(
        result, known, include_group_effects=False
    )
    assert bool(conditional["group_effect_used"].iloc[0])
    assert not np.isclose(
        conditional["location_mean"].iloc[0], population["location_mean"].iloc[0]
    )

    unseen = known.copy()
    unseen["participant_id"] = "NEW"
    predicted = predict_correlated_location_random_slope_scale(result, unseen)
    assert not bool(predicted["group_effect_used"].iloc[0])
    with pytest.raises(SchemaError, match="unseen groups"):
        predict_correlated_location_random_slope_scale(
            result, unseen, allow_new_groups=False
        )

    diagnostics = correlated_location_random_slope_scale_diagnostics(result, data)
    assert np.isfinite(diagnostics["standardized_residual"]).all()
    assert (diagnostics["sigma"] > 0).all()


def test_spec_reuses_random_slope_identifiability_contract() -> None:
    with pytest.raises(ValueError, match="must also appear"):
        CorrelatedLocationRandomSlopeScaleSpec(
            outcome_col="outcome",
            group_col="participant_id",
            random_slope_predictor="condition",
            location_predictors=(),
        )

    data = _synthetic()
    data.loc[data["participant_id"] == "P00", "condition"] = 0.0
    spec = CorrelatedLocationRandomSlopeScaleSpec(
        outcome_col="outcome",
        group_col="participant_id",
        random_slope_predictor="condition",
        location_predictors=("condition",),
        quadrature_points=3,
    )
    with pytest.raises(SchemaError, match="numerically rank deficient"):
        fit_correlated_location_random_slope_scale(data, spec=spec)


@pytest.mark.parametrize("correlation_eta", [-4.0, 4.0])
def test_fit_rejects_successful_outer_optimizer_at_correlation_bound(
    monkeypatch: pytest.MonkeyPatch,
    correlation_eta: float,
) -> None:
    data = _synthetic().groupby("participant_id", sort=False).head(4).reset_index(drop=True)
    spec = CorrelatedLocationRandomSlopeScaleSpec(
        outcome_col="outcome",
        group_col="participant_id",
        random_slope_predictor="condition",
        location_predictors=("condition",),
        quadrature_points=3,
        min_group_size=4,
        max_iter=10,
    )

    def fake_minimize(fun, x0, *, method, **kwargs):
        assert method == "L-BFGS-B"
        forced = np.asarray(x0, dtype=float).copy()
        forced[-1] = correlation_eta
        return SimpleNamespace(
            x=forced,
            success=True,
            status=0,
            message="CONVERGENCE: forced correlation boundary regression",
            nit=1,
            fun=0.0,
        )

    monkeypatch.setattr(correlated_slope_module, "minimize", fake_minimize)
    with pytest.raises(RuntimeError, match="boundary-censored"):
        fit_correlated_location_random_slope_scale(data, spec=spec)


@pytest.mark.parametrize(
    ("theta_index", "boundary"),
    [
        (-4, np.log(correlated_slope_module._MIN_RANDOM_EFFECT_SD)),
        (-4, np.log(correlated_slope_module._MAX_LOCATION_RANDOM_EFFECT_SD)),
        (-3, np.log(correlated_slope_module._MIN_RANDOM_EFFECT_SD)),
        (-3, np.log(correlated_slope_module._MAX_LOCATION_RANDOM_EFFECT_SD)),
        (-2, np.log(correlated_slope_module._MIN_RANDOM_EFFECT_SD)),
        (-2, np.log(correlated_slope_module._MAX_LOG_SCALE_RANDOM_EFFECT_SD)),
    ],
)
def test_fit_rejects_successful_outer_optimizer_at_variance_boundary(
    monkeypatch: pytest.MonkeyPatch,
    theta_index: int,
    boundary: float,
) -> None:
    data = _synthetic().groupby("participant_id", sort=False).head(4).reset_index(drop=True)
    spec = CorrelatedLocationRandomSlopeScaleSpec(
        outcome_col="outcome",
        group_col="participant_id",
        random_slope_predictor="condition",
        location_predictors=("condition",),
        quadrature_points=3,
        min_group_size=4,
        max_iter=10,
    )

    def fake_minimize(fun, x0, *, method, **kwargs):
        assert method == "L-BFGS-B"
        forced = np.asarray(x0, dtype=float).copy()
        forced[theta_index] = boundary
        return SimpleNamespace(
            x=forced,
            success=True,
            status=0,
            message="CONVERGENCE: forced variance boundary regression",
            nit=1,
            fun=0.0,
        )

    monkeypatch.setattr(correlated_slope_module, "minimize", fake_minimize)
    with pytest.raises(RuntimeError, match="boundary"):
        fit_correlated_location_random_slope_scale(data, spec=spec)


def test_certificate_roundtrip_and_canonical_schema(
    fitted: tuple[pd.DataFrame, object],
) -> None:
    _, result = fitted
    certificate = build_correlated_location_random_slope_scale_certificate(result)
    validate_correlated_location_random_slope_scale_certificate(certificate)
    assert certificate["model"]["rho_location_intercept_slope"] == pytest.approx(
        result.rho_location_intercept_slope
    )

    unknown = copy.deepcopy(certificate)
    unknown["model"]["device_specific_validity"] = True
    _resign(unknown)
    with pytest.raises(SchemaError, match="noncanonical schema"):
        validate_correlated_location_random_slope_scale_certificate(unknown)

    noncanonical = copy.deepcopy(certificate)
    noncanonical["model"]["rho_location_intercept_slope"] = "0.5"
    _resign(noncanonical)
    with pytest.raises(SchemaError, match="JSON numbers"):
        validate_correlated_location_random_slope_scale_certificate(noncanonical)


def test_certificate_rejects_resigned_correlation_boundary_and_claim_promotion(
    fitted: tuple[pd.DataFrame, object],
) -> None:
    _, result = fitted
    certificate = build_correlated_location_random_slope_scale_certificate(result)

    boundary = copy.deepcopy(certificate)
    boundary["model"]["rho_location_intercept_slope"] = float(np.tanh(4.0))
    _resign(boundary)
    with pytest.raises(SchemaError, match="artificial optimizer boundary"):
        validate_correlated_location_random_slope_scale_certificate(boundary)

    promoted = copy.deepcopy(certificate)
    promoted["claim_boundary"]["location_slope_log_scale_correlation_modelled"] = True
    body = {
        key: value
        for key, value in promoted.items()
        if key != "certificate_fingerprint_sha256"
    }
    promoted["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    with pytest.raises(SchemaError, match="claim boundary"):
        validate_correlated_location_random_slope_scale_certificate(promoted)


def test_result_mutation_and_resigned_boundary_result_fail_closed(
    fitted: tuple[pd.DataFrame, object],
) -> None:
    data, result = fitted
    original = float(result.location_coef[0])
    result.location_coef[0] = original + 0.3
    try:
        with pytest.raises(SchemaError, match="identity"):
            predict_correlated_location_random_slope_scale(result, data.iloc[[0]])
    finally:
        result.location_coef[0] = original

    certificate = build_correlated_location_random_slope_scale_certificate(result)
    forged_model = copy.deepcopy(certificate["model"])
    forged_model["rho_location_intercept_slope"] = float(np.tanh(4.0))
    forged = replace(
        result,
        rho_location_intercept_slope=float(np.tanh(4.0)),
        model_fingerprint_sha256=benchmark_fingerprint(forged_model),
    )
    with pytest.raises(SchemaError, match="artificial optimizer boundary"):
        build_correlated_location_random_slope_scale_certificate(forged)


def test_freeze_roundtrip_and_overwrite_protection(
    fitted: tuple[pd.DataFrame, object],
    tmp_path: Path,
) -> None:
    _, result = fitted
    path = tmp_path / "correlated-random-slope.json"
    frozen = freeze_correlated_location_random_slope_scale_certificate(result, path)
    payload = json.loads(frozen.read_text(encoding="utf-8"))
    validate_correlated_location_random_slope_scale_certificate(payload)
    with pytest.raises(FileExistsError):
        freeze_correlated_location_random_slope_scale_certificate(result, path)
