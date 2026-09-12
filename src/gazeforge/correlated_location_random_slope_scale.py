"""Correlated participant location-intercept/slope Gaussian location-scale model."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from ._certificate_schema import (
    CERTIFICATE_FIELDS,
    require_canonical_optimizer,
    require_exact_mapping_keys,
    require_finite_json_numbers,
)
from .benchmarks import benchmark_fingerprint
from .exceptions import SchemaError
from .location_random_slope_scale import (
    _MAX_LOCATION_RANDOM_EFFECT_SD,
    _MAX_LOG_SCALE_RANDOM_EFFECT_SD,
    _MIN_RANDOM_EFFECT_SD,
    _adaptive_group_quadrature,
    _numeric_design,
    _prepare_model,
    _quadrature,
    _random_effect_sd_at_numerical_boundary,
    _random_effect_sd_boundary_reached,
    _require_columns,
)
from .location_random_slope_scale import (
    LocationRandomSlopeScaleSpec as _IndependentRandomSlopeSpec,
)
from .location_random_slope_scale import (
    _initial_parameters as _independent_initial_parameters,
)
from .provenance import fingerprint_frame

_CERTIFICATE_SCHEMA = "gazeforge.correlated-location-random-slope-scale-certificate.v1"
_MAX_ABS_CORRELATION_ETA = 4.0
_CORRELATION_ETA_BOUNDARY_ATOL = 1e-6
_MAX_ABS_CERTIFIABLE_RHO = float(
    np.tanh(_MAX_ABS_CORRELATION_ETA - _CORRELATION_ETA_BOUNDARY_ATOL)
)
_MIN_ONE_MINUS_RHO_SQUARED = 1e-6
_CLAIM_BOUNDARY = {
    "joint_location_scale_model": True,
    "participant_random_location_intercept": True,
    "participant_random_location_slope": True,
    "participant_random_log_scale_intercept": True,
    "location_intercept_slope_correlation_modelled": True,
    "location_intercept_log_scale_correlation_modelled": False,
    "location_slope_log_scale_correlation_modelled": False,
    "scale_random_slopes_modelled": False,
    "adaptive_gauss_hermite_quadrature": True,
    "gaussian_conditional_outcome": True,
    "nested_or_crossed_groups_modelled": False,
    "fixed_effect_p_values_provided": False,
    "causal_effects_established": False,
    "device_validity_established": False,
    "measurement_validity_established": False,
    "motion_quality_as_likelihood_weight": False,
    "unseen_group_effects_known": False,
}


@dataclass(frozen=True, slots=True)
class CorrelatedLocationRandomSlopeScaleSpec:
    """Specification for a correlated location intercept/slope random-effects block.

    The conditional model is ``y_i ~ Normal(mu_i, sigma_i)`` with
    ``mu_i = X_i beta + b0_g + b1_g * w_i`` and
    ``log(sigma_i) = Z_i gamma + c_g``. The location effects ``(b0_g, b1_g)``
    are jointly zero-mean Gaussian with estimated correlation. The log-scale
    intercept ``c_g`` is Gaussian and independent of the two location effects.
    """

    outcome_col: str
    group_col: str
    random_slope_predictor: str
    location_predictors: tuple[str, ...] = ()
    scale_predictors: tuple[str, ...] = ()
    quadrature_points: int = 5
    min_group_size: int = 4
    max_iter: int = 400
    tolerance: float = 1e-8

    def __post_init__(self) -> None:
        canonical = _IndependentRandomSlopeSpec(
            outcome_col=self.outcome_col,
            group_col=self.group_col,
            random_slope_predictor=self.random_slope_predictor,
            location_predictors=self.location_predictors,
            scale_predictors=self.scale_predictors,
            quadrature_points=self.quadrature_points,
            min_group_size=self.min_group_size,
            max_iter=self.max_iter,
            tolerance=self.tolerance,
        )
        for field_name, value in canonical.to_dict().items():
            if field_name in {"location_predictors", "scale_predictors"}:
                value = tuple(value)
            object.__setattr__(self, field_name, value)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the canonical specification."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CorrelatedLocationRandomSlopeScaleResult:
    """Fitted model and empirical-Bayes participant-effect summaries."""

    spec: CorrelatedLocationRandomSlopeScaleSpec
    location_terms: tuple[str, ...]
    scale_terms: tuple[str, ...]
    location_coef: np.ndarray
    scale_coef: np.ndarray
    tau_location_intercept: float
    tau_location_slope: float
    tau_scale: float
    rho_location_intercept_slope: float
    log_likelihood: float
    converged: bool
    optimizer_status: int
    optimizer_message: str
    optimizer_iterations: int
    n_obs: int
    n_groups: int
    group_effects: pd.DataFrame
    input_fingerprint_sha256: str
    model_fingerprint_sha256: str

    def fixed_effects(self) -> pd.DataFrame:
        """Return location fixed effects and log-scale fixed effects."""
        _validate_result_identity(self)
        rows: list[dict[str, Any]] = []
        for term, estimate in zip(self.location_terms, self.location_coef, strict=True):
            rows.append(
                {
                    "equation": "location",
                    "term": term,
                    "estimate": float(estimate),
                    "sigma_ratio": np.nan,
                }
            )
        for term, estimate in zip(self.scale_terms, self.scale_coef, strict=True):
            rows.append(
                {
                    "equation": "log_scale",
                    "term": term,
                    "estimate": float(estimate),
                    "sigma_ratio": float(np.exp(estimate)),
                }
            )
        return pd.DataFrame(rows)

    def random_effect_correlation(self) -> float:
        """Return the fitted population location intercept/slope correlation."""
        _validate_result_identity(self)
        return float(self.rho_location_intercept_slope)


def _initial_parameters(prepared: Any) -> np.ndarray:
    independent = _independent_initial_parameters(prepared)
    return np.concatenate([independent, [0.0]])


def _unpack(
    theta: np.ndarray,
    n_location: int,
    n_scale: int,
) -> tuple[np.ndarray, np.ndarray, float, float, float, float]:
    beta = theta[:n_location]
    gamma = theta[n_location : n_location + n_scale]
    tau_intercept = float(np.exp(theta[-4]))
    tau_slope = float(np.exp(theta[-3]))
    tau_scale = float(np.exp(theta[-2]))
    rho = float(np.tanh(theta[-1]))
    return beta, gamma, tau_intercept, tau_slope, tau_scale, rho


def _latent_location_parameterization(
    tau_intercept: float,
    tau_slope: float,
    rho: float,
) -> tuple[float, float]:
    """Map the correlated location block to independent latent effects."""
    one_minus = 1.0 - rho**2
    if (
        not np.isfinite(one_minus)
        or one_minus < _MIN_ONE_MINUS_RHO_SQUARED
        or not np.isfinite(tau_intercept)
        or not np.isfinite(tau_slope)
        or tau_intercept <= 0.0
        or tau_slope <= 0.0
    ):
        raise ValueError("Location random-effect covariance is numerically unsupported.")
    latent_tau_intercept = float(tau_intercept * np.sqrt(one_minus))
    delta = float(-rho * tau_intercept / tau_slope)
    if not np.isfinite(latent_tau_intercept) or not np.isfinite(delta):
        raise ValueError("Location random-effect latent parameterization is non-finite.")
    return latent_tau_intercept, delta


def _correlation_at_numerical_boundary(rho: float) -> bool:
    return not np.isfinite(rho) or abs(rho) >= _MAX_ABS_CERTIFIABLE_RHO


def _latent_intercept_boundary_reached(
    tau_intercept: float,
    tau_slope: float,
    rho: float,
) -> bool:
    try:
        latent_tau_intercept, _ = _latent_location_parameterization(
            tau_intercept, tau_slope, rho
        )
    except ValueError:
        return True
    return _random_effect_sd_at_numerical_boundary(
        latent_tau_intercept,
        upper=_MAX_LOCATION_RANDOM_EFFECT_SD,
    )


def _effective_slope_values(
    slope_values: np.ndarray,
    tau_intercept: float,
    tau_slope: float,
    rho: float,
) -> tuple[np.ndarray, float, float]:
    latent_tau_intercept, delta = _latent_location_parameterization(
        tau_intercept, tau_slope, rho
    )
    effective = np.asarray(slope_values, dtype=float) - delta
    if not np.isfinite(effective).all():
        raise ValueError("Shifted random-slope predictor is non-finite.")
    return effective, latent_tau_intercept, delta


def _objective_factory(prepared: Any, nodes: np.ndarray, log_weight_grid: np.ndarray):
    n_location = prepared.location_design.shape[1]
    n_scale = prepared.scale_design.shape[1]

    def objective(theta: np.ndarray) -> float:
        if not np.isfinite(theta).all():
            return 1e100
        beta, gamma, tau_intercept, tau_slope, tau_scale, rho = _unpack(
            theta, n_location, n_scale
        )
        taus = np.array([tau_intercept, tau_slope, tau_scale], dtype=float)
        if (
            not np.isfinite(taus).all()
            or np.any(taus < _MIN_RANDOM_EFFECT_SD)
            or tau_intercept > _MAX_LOCATION_RANDOM_EFFECT_SD
            or tau_slope > _MAX_LOCATION_RANDOM_EFFECT_SD
            or tau_scale > _MAX_LOG_SCALE_RANDOM_EFFECT_SD
            or 1.0 - rho**2 < _MIN_ONE_MINUS_RHO_SQUARED
        ):
            return 1e100
        try:
            effective_slope, latent_tau_intercept, _ = _effective_slope_values(
                prepared.slope_values,
                tau_intercept,
                tau_slope,
                rho,
            )
        except ValueError:
            return 1e100
        if (
            latent_tau_intercept < _MIN_RANDOM_EFFECT_SD
            or latent_tau_intercept > _MAX_LOCATION_RANDOM_EFFECT_SD
        ):
            return 1e100
        total = 0.0
        for rows in prepared.group_rows:
            group_log_likelihood, _, _, _ = _adaptive_group_quadrature(
                prepared.y[rows],
                prepared.location_design[rows],
                prepared.scale_design[rows],
                effective_slope[rows],
                beta,
                gamma,
                latent_tau_intercept,
                tau_slope,
                tau_scale,
                nodes,
                log_weight_grid,
            )
            if not np.isfinite(group_log_likelihood):
                return 1e100
            total += group_log_likelihood
        return -total

    return objective


def _posterior_group_effects(
    prepared: Any,
    spec: CorrelatedLocationRandomSlopeScaleSpec,
    beta: np.ndarray,
    gamma: np.ndarray,
    tau_intercept: float,
    tau_slope: float,
    tau_scale: float,
    rho: float,
    nodes: np.ndarray,
    log_weight_grid: np.ndarray,
) -> pd.DataFrame:
    effective_slope, latent_tau_intercept, delta = _effective_slope_values(
        prepared.slope_values,
        tau_intercept,
        tau_slope,
        rho,
    )
    transform = np.array(
        [[1.0, -delta, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        dtype=float,
    )
    rows_out: list[dict[str, Any]] = []
    for group_value, rows in zip(prepared.group_levels, prepared.group_rows, strict=True):
        _, latent_grid, probabilities, latent_mode = _adaptive_group_quadrature(
            prepared.y[rows],
            prepared.location_design[rows],
            prepared.scale_design[rows],
            effective_slope[rows],
            beta,
            gamma,
            latent_tau_intercept,
            tau_slope,
            tau_scale,
            nodes,
            log_weight_grid,
        )
        if len(probabilities) == 0:
            raise RuntimeError(
                "Adaptive quadrature failed while recovering correlated random-slope "
                f"group effects for {group_value!r}."
            )
        grid = latent_grid @ transform.T
        mode = transform @ latent_mode
        means = probabilities @ grid
        centered = grid - means
        covariance = (centered.T * probabilities) @ centered
        rows_out.append(
            {
                spec.group_col: group_value,
                "n_obs": int(len(rows)),
                "location_intercept_random_mode": float(mode[0]),
                "location_slope_random_mode": float(mode[1]),
                "log_scale_random_mode": float(mode[2]),
                "location_intercept_random_mean": float(means[0]),
                "location_slope_random_mean": float(means[1]),
                "log_scale_random_mean": float(means[2]),
                "location_intercept_random_sd": float(
                    np.sqrt(max(float(covariance[0, 0]), 0.0))
                ),
                "location_slope_random_sd": float(
                    np.sqrt(max(float(covariance[1, 1]), 0.0))
                ),
                "log_scale_random_sd": float(
                    np.sqrt(max(float(covariance[2, 2]), 0.0))
                ),
                "intercept_slope_posterior_cov": float(covariance[0, 1]),
                "intercept_log_scale_posterior_cov": float(covariance[0, 2]),
                "slope_log_scale_posterior_cov": float(covariance[1, 2]),
                "scale_multiplier_mean": float(probabilities @ np.exp(grid[:, 2])),
            }
        )
    return pd.DataFrame(rows_out)


def _model_identity_payload(
    *,
    spec: CorrelatedLocationRandomSlopeScaleSpec,
    location_terms: tuple[str, ...],
    scale_terms: tuple[str, ...],
    location_coef: np.ndarray,
    scale_coef: np.ndarray,
    tau_intercept: float,
    tau_slope: float,
    tau_scale: float,
    rho: float,
    log_likelihood: float,
    n_obs: int,
    n_groups: int,
    group_effects: pd.DataFrame,
    input_fingerprint: str,
) -> dict[str, Any]:
    return {
        "spec": spec.to_dict(),
        "location_fixed_effects": {
            term: float(value)
            for term, value in zip(location_terms, location_coef, strict=True)
        },
        "scale_fixed_effects": {
            term: float(value)
            for term, value in zip(scale_terms, scale_coef, strict=True)
        },
        "tau_location_intercept": float(tau_intercept),
        "tau_location_slope": float(tau_slope),
        "tau_log_scale": float(tau_scale),
        "rho_location_intercept_slope": float(rho),
        "log_likelihood": float(log_likelihood),
        "n_obs": int(n_obs),
        "n_groups": int(n_groups),
        "group_effects_fingerprint_sha256": fingerprint_frame(group_effects),
        "input_fingerprint_sha256": input_fingerprint,
    }


def fit_correlated_location_random_slope_scale(
    data: pd.DataFrame,
    *,
    spec: CorrelatedLocationRandomSlopeScaleSpec,
    require_convergence: bool = True,
) -> CorrelatedLocationRandomSlopeScaleResult:
    """Fit the correlated location intercept/slope model with 3D AGHQ."""
    prepared = _prepare_model(data, spec)
    initial = _initial_parameters(prepared)
    nodes, log_weight_grid = _quadrature(spec)
    objective = _objective_factory(prepared, nodes, log_weight_grid)
    bounds = [(None, None)] * (len(initial) - 1) + [
        (-_MAX_ABS_CORRELATION_ETA, _MAX_ABS_CORRELATION_ETA)
    ]
    optimized = minimize(
        objective,
        initial,
        method="L-BFGS-B",
        bounds=bounds,
        options={"maxiter": spec.max_iter, "ftol": spec.tolerance},
    )
    if require_convergence and not optimized.success:
        raise RuntimeError(
            "Correlated location random-slope scale optimizer did not converge: "
            f"{optimized.message}"
        )
    correlation_eta = float(np.asarray(optimized.x, dtype=float)[-1])
    if (
        not np.isfinite(correlation_eta)
        or abs(correlation_eta)
        >= _MAX_ABS_CORRELATION_ETA - _CORRELATION_ETA_BOUNDARY_ATOL
    ):
        raise RuntimeError(
            "Correlated location intercept/slope estimate reached the artificial optimizer "
            "bound; the correlation is boundary-censored and is not certifiable."
        )
    n_location = prepared.location_design.shape[1]
    n_scale = prepared.scale_design.shape[1]
    beta, gamma, tau_intercept, tau_slope, tau_scale, rho = _unpack(
        optimized.x, n_location, n_scale
    )
    numeric = np.concatenate(
        [
            beta,
            gamma,
            [tau_intercept, tau_slope, tau_scale, rho, float(optimized.fun)],
        ]
    )
    if not np.isfinite(numeric).all():
        raise RuntimeError(
            "Correlated location random-slope scale fit produced non-finite parameters."
        )
    if _random_effect_sd_boundary_reached(tau_intercept, tau_slope, tau_scale):
        raise RuntimeError(
            "Correlated location random-slope scale random-effect standard deviation "
            "reached an artificial numerical boundary; the variance component is "
            "boundary-censored and is not certifiable."
        )
    if _latent_intercept_boundary_reached(tau_intercept, tau_slope, rho):
        raise RuntimeError(
            "Correlated location random-slope latent covariance factor reached an "
            "artificial numerical boundary and is not certifiable."
        )
    group_effects = _posterior_group_effects(
        prepared,
        spec,
        beta,
        gamma,
        tau_intercept,
        tau_slope,
        tau_scale,
        rho,
        nodes,
        log_weight_grid,
    )
    input_columns = list(
        dict.fromkeys(
            (
                spec.outcome_col,
                spec.group_col,
                *spec.location_predictors,
                *spec.scale_predictors,
            )
        )
    )
    input_fingerprint = fingerprint_frame(data.loc[:, input_columns])
    log_likelihood = -float(optimized.fun)
    identity = _model_identity_payload(
        spec=spec,
        location_terms=prepared.location_terms,
        scale_terms=prepared.scale_terms,
        location_coef=beta,
        scale_coef=gamma,
        tau_intercept=tau_intercept,
        tau_slope=tau_slope,
        tau_scale=tau_scale,
        rho=rho,
        log_likelihood=log_likelihood,
        n_obs=len(data),
        n_groups=len(prepared.group_levels),
        group_effects=group_effects,
        input_fingerprint=input_fingerprint,
    )
    return CorrelatedLocationRandomSlopeScaleResult(
        spec=spec,
        location_terms=prepared.location_terms,
        scale_terms=prepared.scale_terms,
        location_coef=np.array(beta, dtype=float, copy=True),
        scale_coef=np.array(gamma, dtype=float, copy=True),
        tau_location_intercept=float(tau_intercept),
        tau_location_slope=float(tau_slope),
        tau_scale=float(tau_scale),
        rho_location_intercept_slope=float(rho),
        log_likelihood=log_likelihood,
        converged=bool(optimized.success),
        optimizer_status=int(optimized.status),
        optimizer_message=str(optimized.message),
        optimizer_iterations=int(getattr(optimized, "nit", 0)),
        n_obs=int(len(data)),
        n_groups=int(len(prepared.group_levels)),
        group_effects=group_effects,
        input_fingerprint_sha256=input_fingerprint,
        model_fingerprint_sha256=benchmark_fingerprint(identity),
    )


def predict_correlated_location_random_slope_scale(
    result: CorrelatedLocationRandomSlopeScaleResult,
    data: pd.DataFrame,
    *,
    include_group_effects: bool = True,
    allow_new_groups: bool = True,
) -> pd.DataFrame:
    """Predict conditional location and sigma for known or unseen groups."""
    _validate_result_identity(result)
    spec = result.spec
    required = (spec.group_col, *spec.location_predictors, *spec.scale_predictors)
    _require_columns(data, required)
    if data[spec.group_col].isna().any():
        raise SchemaError("Prediction group identities must be complete.")
    location_design, location_terms = _numeric_design(
        data, spec.location_predictors, equation="Location", check_rank=False
    )
    scale_design, scale_terms = _numeric_design(
        data, spec.scale_predictors, equation="Scale", check_rank=False
    )
    if location_terms != result.location_terms or scale_terms != result.scale_terms:
        raise RuntimeError("Prediction design does not match the fitted model terms.")
    slope_values = pd.to_numeric(
        data[spec.random_slope_predictor], errors="coerce"
    ).to_numpy(dtype=float)
    if not np.isfinite(slope_values).all():
        raise SchemaError("Prediction random-slope values must be finite and numeric.")

    location = location_design @ result.location_coef
    log_scale = scale_design @ result.scale_coef
    effects_used = np.zeros(len(data), dtype=bool)
    if include_group_effects:
        effect_table = result.group_effects.set_index(spec.group_col)
        known = data[spec.group_col].isin(effect_table.index).to_numpy(dtype=bool)
        if not allow_new_groups and not known.all():
            unseen = data.loc[~known, spec.group_col].drop_duplicates().tolist()[:10]
            raise SchemaError(f"Prediction contains unseen groups: {unseen}")
        if np.any(known):
            group_values = data.loc[known, spec.group_col]
            location[known] += effect_table.loc[
                group_values, "location_intercept_random_mean"
            ].to_numpy(float)
            location[known] += (
                effect_table.loc[
                    group_values, "location_slope_random_mean"
                ].to_numpy(float)
                * slope_values[known]
            )
            log_scale[known] += effect_table.loc[
                group_values, "log_scale_random_mean"
            ].to_numpy(float)
            effects_used[known] = True
    if np.any((log_scale < -25.0) | (log_scale > 25.0)):
        raise RuntimeError(
            "Predicted log-scale is outside the numerically supported range [-25, 25]."
        )
    output = pd.DataFrame(index=data.index)
    output["location_mean"] = location
    output["log_scale"] = log_scale
    output["sigma"] = np.exp(log_scale)
    output["group_effect_used"] = effects_used
    return output


def correlated_location_random_slope_scale_diagnostics(
    result: CorrelatedLocationRandomSlopeScaleResult,
    data: pd.DataFrame,
) -> pd.DataFrame:
    """Return fitted values and residual diagnostics without inferential tests."""
    _require_columns(data, (result.spec.outcome_col,))
    predicted = predict_correlated_location_random_slope_scale(result, data)
    outcome = pd.to_numeric(
        data[result.spec.outcome_col], errors="coerce"
    ).to_numpy(dtype=float)
    if not np.isfinite(outcome).all():
        raise SchemaError("Outcome values must be finite for diagnostics.")
    residual = outcome - predicted["location_mean"].to_numpy(float)
    output = predicted.copy()
    output["residual"] = residual
    output["standardized_residual"] = residual / predicted["sigma"].to_numpy(float)
    return output


def _current_result_identity(
    result: CorrelatedLocationRandomSlopeScaleResult,
) -> dict[str, Any]:
    return _model_identity_payload(
        spec=result.spec,
        location_terms=result.location_terms,
        scale_terms=result.scale_terms,
        location_coef=result.location_coef,
        scale_coef=result.scale_coef,
        tau_intercept=result.tau_location_intercept,
        tau_slope=result.tau_location_slope,
        tau_scale=result.tau_scale,
        rho=result.rho_location_intercept_slope,
        log_likelihood=result.log_likelihood,
        n_obs=result.n_obs,
        n_groups=result.n_groups,
        group_effects=result.group_effects,
        input_fingerprint=result.input_fingerprint_sha256,
    )


def _is_sha256_hex(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _validate_result_identity(
    result: CorrelatedLocationRandomSlopeScaleResult,
) -> dict[str, Any]:
    identity = _current_result_identity(result)
    expected = benchmark_fingerprint(identity)
    if (
        not _is_sha256_hex(result.model_fingerprint_sha256)
        or result.model_fingerprint_sha256 != expected
    ):
        raise SchemaError(
            "Correlated location random-slope scale result identity no longer matches "
            "the fitted model."
        )
    if not _is_sha256_hex(result.input_fingerprint_sha256):
        raise SchemaError(
            "Correlated location random-slope scale input fingerprint is invalid."
        )
    taus = np.array(
        [
            result.tau_location_intercept,
            result.tau_location_slope,
            result.tau_scale,
        ],
        dtype=float,
    )
    if not np.isfinite(taus).all() or np.any(taus <= 0.0):
        raise SchemaError("Random-effect standard deviations must be finite and positive.")
    if _random_effect_sd_boundary_reached(
        result.tau_location_intercept,
        result.tau_location_slope,
        result.tau_scale,
    ):
        raise SchemaError(
            "Correlated location random-slope scale random-effect standard deviation "
            "is at an artificial numerical boundary and is not certifiable."
        )
    rho = float(result.rho_location_intercept_slope)
    if _correlation_at_numerical_boundary(rho):
        raise SchemaError(
            "Location intercept/slope correlation is at the artificial optimizer "
            "boundary and is not certifiable."
        )
    if _latent_intercept_boundary_reached(
        result.tau_location_intercept,
        result.tau_location_slope,
        rho,
    ):
        raise SchemaError(
            "Correlated location random-slope latent covariance factor is at an "
            "artificial numerical boundary and is not certifiable."
        )
    if result.n_obs < result.n_groups * result.spec.min_group_size:
        raise SchemaError(
            "Correlated location random-slope scale result group/sample counts are "
            "inconsistent."
        )
    return identity


def build_correlated_location_random_slope_scale_certificate(
    result: CorrelatedLocationRandomSlopeScaleResult,
) -> dict[str, Any]:
    """Build a deterministic scientific-claim certificate for a fitted model."""
    identity = _validate_result_identity(result)
    body = {
        "schema": _CERTIFICATE_SCHEMA,
        "model": identity,
        "model_fingerprint_sha256": result.model_fingerprint_sha256,
        "optimizer": {
            "converged": bool(result.converged),
            "status": int(result.optimizer_status),
            "message": result.optimizer_message,
            "iterations": int(result.optimizer_iterations),
        },
        "claim_boundary": dict(_CLAIM_BOUNDARY),
    }
    return {**body, "certificate_fingerprint_sha256": benchmark_fingerprint(body)}


def validate_correlated_location_random_slope_scale_certificate(
    certificate: dict[str, Any],
) -> None:
    """Fail closed on certificate tampering or scientific-claim promotion."""
    require_exact_mapping_keys(
        certificate,
        CERTIFICATE_FIELDS,
        context="Correlated location random-slope scale certificate",
    )
    if certificate.get("schema") != _CERTIFICATE_SCHEMA:
        raise SchemaError(
            "Unsupported correlated location random-slope scale certificate schema."
        )
    fingerprint = certificate.get("certificate_fingerprint_sha256")
    body = {
        key: value
        for key, value in certificate.items()
        if key != "certificate_fingerprint_sha256"
    }
    if not _is_sha256_hex(fingerprint) or fingerprint != benchmark_fingerprint(body):
        raise SchemaError(
            "Correlated location random-slope scale certificate fingerprint mismatch."
        )
    if certificate.get("claim_boundary") != _CLAIM_BOUNDARY:
        raise SchemaError(
            "Correlated location random-slope scale scientific claim boundary was altered."
        )
    require_canonical_optimizer(
        certificate.get("optimizer"),
        context="correlated location random-slope scale",
    )
    model = certificate.get("model")
    required_model_fields = (
        "spec",
        "location_fixed_effects",
        "scale_fixed_effects",
        "tau_location_intercept",
        "tau_location_slope",
        "tau_log_scale",
        "rho_location_intercept_slope",
        "log_likelihood",
        "n_obs",
        "n_groups",
        "group_effects_fingerprint_sha256",
        "input_fingerprint_sha256",
    )
    require_exact_mapping_keys(
        model,
        required_model_fields,
        context="Correlated location random-slope scale model payload",
    )
    model_fingerprint = certificate.get("model_fingerprint_sha256")
    if (
        not _is_sha256_hex(model_fingerprint)
        or model_fingerprint != benchmark_fingerprint(model)
    ):
        raise SchemaError(
            "Correlated location random-slope scale model fingerprint mismatch."
        )
    try:
        canonical_spec = CorrelatedLocationRandomSlopeScaleSpec(**model["spec"])
    except (TypeError, ValueError) as exc:
        raise SchemaError(
            "Correlated location random-slope scale certificate has an invalid model spec."
        ) from exc
    if benchmark_fingerprint(canonical_spec.to_dict()) != benchmark_fingerprint(
        model["spec"]
    ):
        raise SchemaError(
            "Correlated location random-slope scale certificate model spec is not canonical."
        )
    expected_location_terms = {"Intercept", *canonical_spec.location_predictors}
    expected_scale_terms = {"Intercept", *canonical_spec.scale_predictors}
    location_effects = model["location_fixed_effects"]
    scale_effects = model["scale_fixed_effects"]
    if (
        not isinstance(location_effects, dict)
        or set(location_effects) != expected_location_terms
    ):
        raise SchemaError("Location fixed-effect terms do not match the certified model spec.")
    if (
        not isinstance(scale_effects, dict)
        or set(scale_effects) != expected_scale_terms
    ):
        raise SchemaError("Scale fixed-effect terms do not match the certified model spec.")
    if not _is_sha256_hex(model["group_effects_fingerprint_sha256"]):
        raise SchemaError("Group-effects fingerprint is invalid.")
    if not _is_sha256_hex(model["input_fingerprint_sha256"]):
        raise SchemaError("Input fingerprint is invalid.")
    numeric = [
        model["tau_location_intercept"],
        model["tau_location_slope"],
        model["tau_log_scale"],
        model["rho_location_intercept_slope"],
        model["log_likelihood"],
        *location_effects.values(),
        *scale_effects.values(),
    ]
    require_finite_json_numbers(
        numeric,
        context="Correlated location random-slope scale certificate estimates",
    )
    tau_intercept = float(model["tau_location_intercept"])
    tau_slope = float(model["tau_location_slope"])
    tau_scale = float(model["tau_log_scale"])
    rho = float(model["rho_location_intercept_slope"])
    if tau_intercept <= 0.0 or tau_slope <= 0.0 or tau_scale <= 0.0:
        raise SchemaError("Random-effect standard deviations must be positive.")
    if _random_effect_sd_boundary_reached(tau_intercept, tau_slope, tau_scale):
        raise SchemaError(
            "Certified random-effect standard deviation is at an artificial numerical "
            "boundary."
        )
    if _correlation_at_numerical_boundary(rho):
        raise SchemaError(
            "Certified location intercept/slope correlation is at the artificial optimizer "
            "boundary."
        )
    if _latent_intercept_boundary_reached(tau_intercept, tau_slope, rho):
        raise SchemaError(
            "Certified latent covariance factor is at an artificial numerical boundary."
        )
    n_obs = model["n_obs"]
    n_groups = model["n_groups"]
    if not isinstance(n_obs, int) or isinstance(n_obs, bool) or n_obs <= 0:
        raise SchemaError("n_obs must be a positive integer.")
    if not isinstance(n_groups, int) or isinstance(n_groups, bool) or n_groups < 2:
        raise SchemaError("n_groups must be an integer of at least two.")
    if n_obs < n_groups * canonical_spec.min_group_size:
        raise SchemaError("Certified group/sample counts violate min_group_size.")


def freeze_correlated_location_random_slope_scale_certificate(
    result: CorrelatedLocationRandomSlopeScaleResult,
    path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Validate and freeze a certificate; protect existing files by default."""
    certificate = build_correlated_location_random_slope_scale_certificate(result)
    validate_correlated_location_random_slope_scale_certificate(certificate)
    target = Path(path)
    if target.exists() and not overwrite:
        raise FileExistsError(
            "Correlated location random-slope scale certificate already exists: "
            f"{target}"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(certificate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target
