"""Gaussian hierarchical location-scale model with one participant random slope."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from numpy.polynomial.hermite import hermgauss
from scipy.optimize import minimize
from scipy.special import logsumexp

from ._certificate_schema import (
    CERTIFICATE_FIELDS,
    require_canonical_optimizer,
    require_exact_mapping_keys,
    require_finite_json_numbers,
)
from .benchmarks import benchmark_fingerprint
from .exceptions import SchemaError
from .provenance import fingerprint_frame

_CERTIFICATE_SCHEMA = "gazeforge.location-random-slope-scale-certificate.v1"
_LOG_2PI = float(np.log(2.0 * np.pi))
_LOG_2 = float(np.log(2.0))
_MIN_RANDOM_EFFECT_SD = 1e-8
_MAX_LOCATION_RANDOM_EFFECT_SD = 1e8
_MAX_LOG_SCALE_RANDOM_EFFECT_SD = 20.0
_RANDOM_EFFECT_LOG_BOUNDARY_ATOL = 1e-6
_CLAIM_BOUNDARY = {
    "joint_location_scale_model": True,
    "participant_random_location_intercept": True,
    "participant_random_location_slope": True,
    "participant_random_log_scale_intercept": True,
    "population_random_effect_correlations_modelled": False,
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
class LocationRandomSlopeScaleSpec:
    """Specification for one participant random slope in the location equation.

    The conditional model is ``y_i ~ Normal(mu_i, sigma_i)`` with

    ``mu_i = X_i beta + b0_g + b1_g * w_i``
    ``log(sigma_i) = Z_i gamma + c_g``

    where ``w`` is ``random_slope_predictor`` and ``(b0_g, b1_g, c_g)`` are
    independent zero-mean Gaussian population effects. The random-slope
    predictor must also appear in ``location_predictors`` so the model contains
    the corresponding population-average fixed slope.
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
        for name, value in (
            ("outcome_col", self.outcome_col),
            ("group_col", self.group_col),
            ("random_slope_predictor", self.random_slope_predictor),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string.")
            object.__setattr__(self, name, value.strip())
        if len({self.outcome_col, self.group_col, self.random_slope_predictor}) < 3:
            raise ValueError(
                "outcome_col, group_col, and random_slope_predictor must be distinct columns."
            )
        location = _canonical_predictor_names(self.location_predictors, "location_predictors")
        scale = _canonical_predictor_names(self.scale_predictors, "scale_predictors")
        if self.random_slope_predictor not in location:
            raise ValueError(
                "random_slope_predictor must also appear in location_predictors so its "
                "population-average fixed slope is estimated."
            )
        collisions = sorted((set(location) | set(scale)) & {self.outcome_col, self.group_col})
        if collisions:
            raise ValueError(
                "Outcome/group columns cannot also be model predictors: " f"{collisions}"
            )
        q = int(self.quadrature_points)
        if q < 3 or q > 9 or q % 2 == 0:
            raise ValueError("quadrature_points must be an odd integer from 3 through 9.")
        min_group_size = int(self.min_group_size)
        if min_group_size < 3:
            raise ValueError("min_group_size must be at least 3 for a participant random slope.")
        max_iter = int(self.max_iter)
        if max_iter < 1:
            raise ValueError("max_iter must be positive.")
        tolerance = float(self.tolerance)
        if not np.isfinite(tolerance) or tolerance <= 0:
            raise ValueError("tolerance must be finite and positive.")
        object.__setattr__(self, "location_predictors", location)
        object.__setattr__(self, "scale_predictors", scale)
        object.__setattr__(self, "quadrature_points", q)
        object.__setattr__(self, "min_group_size", min_group_size)
        object.__setattr__(self, "max_iter", max_iter)
        object.__setattr__(self, "tolerance", tolerance)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the canonical specification."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LocationRandomSlopeScaleResult:
    """Fitted model and empirical-Bayes participant-effect summaries."""

    spec: LocationRandomSlopeScaleSpec
    location_terms: tuple[str, ...]
    scale_terms: tuple[str, ...]
    location_coef: np.ndarray
    scale_coef: np.ndarray
    tau_location_intercept: float
    tau_location_slope: float
    tau_scale: float
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


@dataclass(frozen=True, slots=True)
class _PreparedModel:
    y: np.ndarray
    location_design: np.ndarray
    scale_design: np.ndarray
    slope_values: np.ndarray
    group_levels: tuple[Any, ...]
    group_rows: tuple[np.ndarray, ...]
    location_terms: tuple[str, ...]
    scale_terms: tuple[str, ...]


def _canonical_predictor_names(values: tuple[str, ...], name: str) -> tuple[str, ...]:
    result = tuple(values)
    if any(not isinstance(value, str) or not value.strip() for value in result):
        raise ValueError(f"{name} must contain only non-empty strings.")
    result = tuple(value.strip() for value in result)
    if len(set(result)) != len(result):
        raise ValueError(f"{name} must not contain duplicate columns.")
    if "Intercept" in result:
        raise ValueError(f"{name} cannot use the reserved term name 'Intercept'.")
    return result


def _require_columns(data: pd.DataFrame, columns: tuple[str, ...]) -> None:
    missing = [column for column in columns if column not in data.columns]
    if missing:
        raise SchemaError(f"Missing columns for location random-slope scale model: {missing}")


def _numeric_design(
    data: pd.DataFrame,
    predictors: tuple[str, ...],
    *,
    equation: str,
    check_rank: bool = True,
) -> tuple[np.ndarray, tuple[str, ...]]:
    columns = [np.ones(len(data), dtype=float)]
    terms = ["Intercept"]
    for predictor in predictors:
        values = pd.to_numeric(data[predictor], errors="coerce").to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise SchemaError(f"{equation} predictor '{predictor}' must be finite and numeric.")
        columns.append(values)
        terms.append(predictor)
    design = np.column_stack(columns)
    if check_rank and np.linalg.matrix_rank(design) < design.shape[1]:
        raise SchemaError(f"{equation} design matrix is rank deficient.")
    return design, tuple(terms)


def _prepare_model(data: pd.DataFrame, spec: LocationRandomSlopeScaleSpec) -> _PreparedModel:
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data must be a pandas DataFrame.")
    if data.empty:
        raise SchemaError("Location random-slope scale fitting requires at least one row.")
    required = (
        spec.outcome_col,
        spec.group_col,
        *spec.location_predictors,
        *spec.scale_predictors,
    )
    _require_columns(data, required)
    if data[spec.group_col].isna().any():
        raise SchemaError("group_col must be complete; missing group identity is not allowed.")
    y = pd.to_numeric(data[spec.outcome_col], errors="coerce").to_numpy(dtype=float)
    if not np.isfinite(y).all():
        raise SchemaError("Outcome values must be finite and numeric.")
    location_design, location_terms = _numeric_design(
        data, spec.location_predictors, equation="Location"
    )
    scale_design, scale_terms = _numeric_design(data, spec.scale_predictors, equation="Scale")
    slope_values = pd.to_numeric(
        data[spec.random_slope_predictor], errors="coerce"
    ).to_numpy(dtype=float)
    if not np.isfinite(slope_values).all():
        raise SchemaError("Random-slope predictor must be finite and numeric.")

    group_codes, levels = pd.factorize(data[spec.group_col], sort=False)
    n_groups = len(levels)
    if n_groups < 2:
        raise SchemaError("Hierarchical random-slope fitting requires at least two groups.")
    sizes = np.bincount(group_codes, minlength=n_groups)
    too_small = np.flatnonzero(sizes < spec.min_group_size)
    if len(too_small):
        labels = [levels[index] for index in too_small[:10]]
        raise SchemaError(
            f"Every group needs at least {spec.min_group_size} observations; "
            f"undersized groups include {labels}."
        )
    group_rows = tuple(np.flatnonzero(group_codes == index) for index in range(n_groups))
    rank_deficient_groups = []
    for index, rows in enumerate(group_rows):
        participant_slope_design = np.column_stack(
            [np.ones(len(rows), dtype=float), slope_values[rows]]
        )
        if np.linalg.matrix_rank(participant_slope_design) < 2:
            rank_deficient_groups.append(levels[index])
    if rank_deficient_groups:
        raise SchemaError(
            "Every group random-slope design [Intercept, random_slope_predictor] must "
            "have numerical rank 2; numerically rank deficient groups include "
            f"{rank_deficient_groups[:10]}. Consider centring or scaling the random-slope "
            "predictor when extreme offsets or magnitudes cause numerical collinearity."
        )
    return _PreparedModel(
        y=y,
        location_design=location_design,
        scale_design=scale_design,
        slope_values=slope_values,
        group_levels=tuple(levels.tolist()),
        group_rows=group_rows,
        location_terms=location_terms,
        scale_terms=scale_terms,
    )


def _initial_parameters(prepared: _PreparedModel) -> np.ndarray:
    beta = np.linalg.lstsq(prepared.location_design, prepared.y, rcond=None)[0]
    residual = prepared.y - prepared.location_design @ beta
    residual_sd = max(float(np.std(residual, ddof=1)), 1e-3)
    gamma = np.zeros(prepared.scale_design.shape[1], dtype=float)
    gamma[0] = np.log(residual_sd)

    group_intercepts: list[float] = []
    group_slopes: list[float] = []
    relative_log_scales: list[float] = []
    for rows in prepared.group_rows:
        w = prepared.slope_values[rows]
        local = np.column_stack([np.ones(len(rows), dtype=float), w])
        coef = np.linalg.lstsq(local, residual[rows], rcond=None)[0]
        group_intercepts.append(float(coef[0]))
        group_slopes.append(float(coef[1]))
        local_residual = residual[rows] - local @ coef
        group_sd = max(float(np.std(local_residual, ddof=1)), 1e-3)
        relative_log_scales.append(np.log(group_sd) - np.log(residual_sd))

    tau_intercept = max(
        float(np.std(group_intercepts, ddof=1)), residual_sd * 0.05, 1e-3
    )
    tau_slope = max(float(np.std(group_slopes, ddof=1)), residual_sd * 0.02, 1e-3)
    tau_scale = max(float(np.std(relative_log_scales, ddof=1)), 0.05)
    return np.concatenate(
        [
            beta,
            gamma,
            [np.log(tau_intercept), np.log(tau_slope), np.log(tau_scale)],
        ]
    )


def _quadrature(spec: LocationRandomSlopeScaleSpec) -> tuple[np.ndarray, np.ndarray]:
    nodes, weights = hermgauss(spec.quadrature_points)
    log_weight_grid = (
        np.log(weights)[:, None, None]
        + np.log(weights)[None, :, None]
        + np.log(weights)[None, None, :]
    ).ravel()
    return nodes, log_weight_grid


def _unpack(
    theta: np.ndarray, n_location: int, n_scale: int
) -> tuple[np.ndarray, np.ndarray, float, float, float]:
    beta = theta[:n_location]
    gamma = theta[n_location : n_location + n_scale]
    tau_intercept = float(np.exp(theta[-3]))
    tau_slope = float(np.exp(theta[-2]))
    tau_scale = float(np.exp(theta[-1]))
    return beta, gamma, tau_intercept, tau_slope, tau_scale


def _random_effect_sd_at_numerical_boundary(
    value: float,
    *,
    upper: float,
) -> bool:
    if not np.isfinite(value) or value <= 0.0:
        return False
    log_value = float(np.log(value))
    return (
        log_value
        <= np.log(_MIN_RANDOM_EFFECT_SD) + _RANDOM_EFFECT_LOG_BOUNDARY_ATOL
        or log_value >= np.log(upper) - _RANDOM_EFFECT_LOG_BOUNDARY_ATOL
    )


def _random_effect_sd_boundary_reached(
    tau_intercept: float,
    tau_slope: float,
    tau_scale: float,
) -> bool:
    return (
        _random_effect_sd_at_numerical_boundary(
            tau_intercept,
            upper=_MAX_LOCATION_RANDOM_EFFECT_SD,
        )
        or _random_effect_sd_at_numerical_boundary(
            tau_slope,
            upper=_MAX_LOCATION_RANDOM_EFFECT_SD,
        )
        or _random_effect_sd_at_numerical_boundary(
            tau_scale,
            upper=_MAX_LOG_SCALE_RANDOM_EFFECT_SD,
        )
    )


def _group_log_integrand(
    random_effects: np.ndarray,
    y: np.ndarray,
    location_design: np.ndarray,
    scale_design: np.ndarray,
    slope_values: np.ndarray,
    beta: np.ndarray,
    gamma: np.ndarray,
    tau_intercept: float,
    tau_slope: float,
    tau_scale: float,
) -> tuple[float, np.ndarray, np.ndarray]:
    location_intercept, location_slope, scale_effect = random_effects
    residual = y - (
        location_design @ beta + location_intercept + location_slope * slope_values
    )
    log_scale = scale_design @ gamma + scale_effect
    if np.any((log_scale < -25.0) | (log_scale > 25.0)):
        return -np.inf, np.zeros(3, dtype=float), np.eye(3, dtype=float)
    inverse_variance = np.exp(-2.0 * log_scale)
    precisions = np.array(
        [
            1.0 / tau_intercept**2,
            1.0 / tau_slope**2,
            1.0 / tau_scale**2,
        ],
        dtype=float,
    )
    prior_quadratic = float(np.sum(np.asarray(random_effects, dtype=float) ** 2 * precisions))
    log_value = float(
        np.sum(-0.5 * _LOG_2PI - log_scale - 0.5 * residual**2 * inverse_variance)
        - 1.5 * _LOG_2PI
        - np.log(tau_intercept)
        - np.log(tau_slope)
        - np.log(tau_scale)
        - 0.5 * prior_quadratic
    )
    weighted_residual = residual * inverse_variance
    likelihood_cross_intercept_scale = 2.0 * np.sum(weighted_residual)
    likelihood_cross_slope_scale = 2.0 * np.sum(slope_values * weighted_residual)
    gradient = np.array(
        [
            np.sum(weighted_residual) - location_intercept * precisions[0],
            np.sum(slope_values * weighted_residual) - location_slope * precisions[1],
            np.sum(-1.0 + residual**2 * inverse_variance) - scale_effect * precisions[2],
        ],
        dtype=float,
    )
    negative_hessian = np.array(
        [
            [
                np.sum(inverse_variance) + precisions[0],
                np.sum(slope_values * inverse_variance),
                likelihood_cross_intercept_scale,
            ],
            [
                np.sum(slope_values * inverse_variance),
                np.sum(slope_values**2 * inverse_variance) + precisions[1],
                likelihood_cross_slope_scale,
            ],
            [
                likelihood_cross_intercept_scale,
                likelihood_cross_slope_scale,
                2.0 * np.sum(residual**2 * inverse_variance) + precisions[2],
            ],
        ],
        dtype=float,
    )
    return log_value, gradient, negative_hessian


def _node_triples(nodes: np.ndarray) -> np.ndarray:
    return np.array(
        [(first, second, third) for first in nodes for second in nodes for third in nodes],
        dtype=float,
    )


def _adaptive_group_quadrature(
    y: np.ndarray,
    location_design: np.ndarray,
    scale_design: np.ndarray,
    slope_values: np.ndarray,
    beta: np.ndarray,
    gamma: np.ndarray,
    tau_intercept: float,
    tau_slope: float,
    tau_scale: float,
    nodes: np.ndarray,
    log_weight_grid: np.ndarray,
) -> tuple[float, np.ndarray, np.ndarray, np.ndarray]:
    def negative_log_posterior(random_effects: np.ndarray) -> float:
        value, _, _ = _group_log_integrand(
            random_effects,
            y,
            location_design,
            scale_design,
            slope_values,
            beta,
            gamma,
            tau_intercept,
            tau_slope,
            tau_scale,
        )
        return 1e100 if not np.isfinite(value) else -value

    def negative_gradient(random_effects: np.ndarray) -> np.ndarray:
        value, gradient, _ = _group_log_integrand(
            random_effects,
            y,
            location_design,
            scale_design,
            slope_values,
            beta,
            gamma,
            tau_intercept,
            tau_slope,
            tau_scale,
        )
        if not np.isfinite(value):
            return np.zeros(3, dtype=float)
        return -gradient

    def negative_hessian_function(random_effects: np.ndarray) -> np.ndarray:
        value, _, negative_hessian = _group_log_integrand(
            random_effects,
            y,
            location_design,
            scale_design,
            slope_values,
            beta,
            gamma,
            tau_intercept,
            tau_slope,
            tau_scale,
        )
        if not np.isfinite(value) or not np.isfinite(negative_hessian).all():
            return np.eye(3, dtype=float)
        return negative_hessian

    mode_result = minimize(
        negative_log_posterior,
        np.zeros(3, dtype=float),
        jac=negative_gradient,
        hess=negative_hessian_function,
        method="trust-exact",
        options={"gtol": 1e-8, "maxiter": 120},
    )
    mode = np.asarray(mode_result.x, dtype=float)
    mode_value, mode_gradient, negative_hessian = _group_log_integrand(
        mode,
        y,
        location_design,
        scale_design,
        slope_values,
        beta,
        gamma,
        tau_intercept,
        tau_slope,
        tau_scale,
    )
    if (
        not np.isfinite(mode_value)
        or not np.isfinite(mode).all()
        or not np.isfinite(negative_hessian).all()
        or (not mode_result.success and np.linalg.norm(mode_gradient) > 1e-5)
    ):
        return -np.inf, np.empty((0, 3)), np.empty(0), mode
    sign, log_determinant = np.linalg.slogdet(negative_hessian)
    if sign <= 0:
        return -np.inf, np.empty((0, 3)), np.empty(0), mode
    try:
        cholesky = np.linalg.cholesky(negative_hessian)
    except np.linalg.LinAlgError:
        return -np.inf, np.empty((0, 3)), np.empty(0), mode
    inverse_root = np.linalg.inv(cholesky.T)
    triples = _node_triples(nodes)
    random_effect_grid = mode[None, :] + np.sqrt(2.0) * (triples @ inverse_root.T)
    adjusted_log_values = np.empty(len(triples), dtype=float)
    for index, (random_effects, node_triple) in enumerate(
        zip(random_effect_grid, triples, strict=True)
    ):
        value, _, _ = _group_log_integrand(
            random_effects,
            y,
            location_design,
            scale_design,
            slope_values,
            beta,
            gamma,
            tau_intercept,
            tau_slope,
            tau_scale,
        )
        adjusted_log_values[index] = value + float(node_triple @ node_triple)
    weighted = log_weight_grid + adjusted_log_values
    log_normalizer = float(logsumexp(weighted))
    if not np.isfinite(log_normalizer):
        return -np.inf, np.empty((0, 3)), np.empty(0), mode
    log_integral = float(1.5 * _LOG_2 - 0.5 * log_determinant + log_normalizer)
    probabilities = np.exp(weighted - log_normalizer)
    if not np.isfinite(probabilities).all() or not np.isclose(probabilities.sum(), 1.0):
        return -np.inf, np.empty((0, 3)), np.empty(0), mode
    return log_integral, random_effect_grid, probabilities, mode


def _objective_factory(
    prepared: _PreparedModel,
    nodes: np.ndarray,
    log_weight_grid: np.ndarray,
):
    n_location = prepared.location_design.shape[1]
    n_scale = prepared.scale_design.shape[1]

    def objective(theta: np.ndarray) -> float:
        if not np.isfinite(theta).all():
            return 1e100
        beta, gamma, tau_intercept, tau_slope, tau_scale = _unpack(
            theta, n_location, n_scale
        )
        taus = np.array([tau_intercept, tau_slope, tau_scale], dtype=float)
        if (
            not np.isfinite(taus).all()
            or np.any(taus < _MIN_RANDOM_EFFECT_SD)
            or tau_intercept > _MAX_LOCATION_RANDOM_EFFECT_SD
            or tau_slope > _MAX_LOCATION_RANDOM_EFFECT_SD
            or tau_scale > _MAX_LOG_SCALE_RANDOM_EFFECT_SD
        ):
            return 1e100
        total = 0.0
        for rows in prepared.group_rows:
            group_log_likelihood, _, _, _ = _adaptive_group_quadrature(
                prepared.y[rows],
                prepared.location_design[rows],
                prepared.scale_design[rows],
                prepared.slope_values[rows],
                beta,
                gamma,
                tau_intercept,
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
    prepared: _PreparedModel,
    spec: LocationRandomSlopeScaleSpec,
    beta: np.ndarray,
    gamma: np.ndarray,
    tau_intercept: float,
    tau_slope: float,
    tau_scale: float,
    nodes: np.ndarray,
    log_weight_grid: np.ndarray,
) -> pd.DataFrame:
    rows_out: list[dict[str, Any]] = []
    for group_value, rows in zip(prepared.group_levels, prepared.group_rows, strict=True):
        _, grid, probabilities, mode = _adaptive_group_quadrature(
            prepared.y[rows],
            prepared.location_design[rows],
            prepared.scale_design[rows],
            prepared.slope_values[rows],
            beta,
            gamma,
            tau_intercept,
            tau_slope,
            tau_scale,
            nodes,
            log_weight_grid,
        )
        if len(probabilities) == 0:
            raise RuntimeError(
                "Adaptive quadrature failed while recovering group effects "
                f"for {group_value!r}."
            )
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
    spec: LocationRandomSlopeScaleSpec,
    location_terms: tuple[str, ...],
    scale_terms: tuple[str, ...],
    location_coef: np.ndarray,
    scale_coef: np.ndarray,
    tau_intercept: float,
    tau_slope: float,
    tau_scale: float,
    log_likelihood: float,
    n_obs: int,
    n_groups: int,
    group_effects: pd.DataFrame,
    input_fingerprint: str,
) -> dict[str, Any]:
    return {
        "spec": spec.to_dict(),
        "location_fixed_effects": {
            term: float(value) for term, value in zip(location_terms, location_coef, strict=True)
        },
        "scale_fixed_effects": {
            term: float(value) for term, value in zip(scale_terms, scale_coef, strict=True)
        },
        "tau_location_intercept": float(tau_intercept),
        "tau_location_slope": float(tau_slope),
        "tau_log_scale": float(tau_scale),
        "population_random_effect_correlations": "independent",
        "log_likelihood": float(log_likelihood),
        "n_obs": int(n_obs),
        "n_groups": int(n_groups),
        "group_effects_fingerprint_sha256": fingerprint_frame(group_effects),
        "input_fingerprint_sha256": input_fingerprint,
    }


def fit_location_random_slope_scale(
    data: pd.DataFrame,
    *,
    spec: LocationRandomSlopeScaleSpec,
    require_convergence: bool = True,
) -> LocationRandomSlopeScaleResult:
    """Fit the independent three-effect random-slope location-scale model by 3D AGHQ."""
    prepared = _prepare_model(data, spec)
    initial = _initial_parameters(prepared)
    nodes, log_weight_grid = _quadrature(spec)
    objective = _objective_factory(prepared, nodes, log_weight_grid)
    optimized = minimize(
        objective,
        initial,
        method="L-BFGS-B",
        options={"maxiter": spec.max_iter, "ftol": spec.tolerance},
    )
    if require_convergence and not optimized.success:
        raise RuntimeError(
            "Location random-slope scale optimizer did not converge: " f"{optimized.message}"
        )
    n_location = prepared.location_design.shape[1]
    n_scale = prepared.scale_design.shape[1]
    beta, gamma, tau_intercept, tau_slope, tau_scale = _unpack(
        optimized.x, n_location, n_scale
    )
    numeric = np.concatenate(
        [
            beta,
            gamma,
            [tau_intercept, tau_slope, tau_scale, float(optimized.fun)],
        ]
    )
    if not np.isfinite(numeric).all():
        raise RuntimeError("Location random-slope scale fit produced non-finite parameters.")
    if _random_effect_sd_boundary_reached(tau_intercept, tau_slope, tau_scale):
        raise RuntimeError(
            "Location random-slope scale random-effect standard deviation reached an "
            "artificial numerical boundary; the variance component is "
            "boundary-censored and is not certifiable."
        )
    group_effects = _posterior_group_effects(
        prepared,
        spec,
        beta,
        gamma,
        tau_intercept,
        tau_slope,
        tau_scale,
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
        log_likelihood=log_likelihood,
        n_obs=len(data),
        n_groups=len(prepared.group_levels),
        group_effects=group_effects,
        input_fingerprint=input_fingerprint,
    )
    return LocationRandomSlopeScaleResult(
        spec=spec,
        location_terms=prepared.location_terms,
        scale_terms=prepared.scale_terms,
        location_coef=np.array(beta, dtype=float, copy=True),
        scale_coef=np.array(gamma, dtype=float, copy=True),
        tau_location_intercept=float(tau_intercept),
        tau_location_slope=float(tau_slope),
        tau_scale=float(tau_scale),
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


def predict_location_random_slope_scale(
    result: LocationRandomSlopeScaleResult,
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
                effect_table.loc[group_values, "location_slope_random_mean"].to_numpy(float)
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


def location_random_slope_scale_diagnostics(
    result: LocationRandomSlopeScaleResult, data: pd.DataFrame
) -> pd.DataFrame:
    """Return fitted values and residual diagnostics without inferential tests."""
    _require_columns(data, (result.spec.outcome_col,))
    predicted = predict_location_random_slope_scale(result, data)
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


def _current_result_identity(result: LocationRandomSlopeScaleResult) -> dict[str, Any]:
    return _model_identity_payload(
        spec=result.spec,
        location_terms=result.location_terms,
        scale_terms=result.scale_terms,
        location_coef=result.location_coef,
        scale_coef=result.scale_coef,
        tau_intercept=result.tau_location_intercept,
        tau_slope=result.tau_location_slope,
        tau_scale=result.tau_scale,
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
    result: LocationRandomSlopeScaleResult,
) -> dict[str, Any]:
    identity = _current_result_identity(result)
    expected = benchmark_fingerprint(identity)
    if (
        not _is_sha256_hex(result.model_fingerprint_sha256)
        or result.model_fingerprint_sha256 != expected
    ):
        raise SchemaError(
            "Location random-slope scale result identity no longer matches the fitted model."
        )
    if not _is_sha256_hex(result.input_fingerprint_sha256):
        raise SchemaError("Location random-slope scale input fingerprint is invalid.")
    taus = np.array(
        [
            result.tau_location_intercept,
            result.tau_location_slope,
            result.tau_scale,
        ],
        dtype=float,
    )
    if not np.isfinite(taus).all() or np.any(taus <= 0):
        raise SchemaError("Random-effect standard deviations must be finite and positive.")
    if _random_effect_sd_boundary_reached(
        result.tau_location_intercept,
        result.tau_location_slope,
        result.tau_scale,
    ):
        raise SchemaError(
            "Location random-slope scale random-effect standard deviation is at an "
            "artificial numerical boundary and is not certifiable."
        )
    if result.n_obs < result.n_groups * result.spec.min_group_size:
        raise SchemaError(
            "Location random-slope scale result group/sample counts are inconsistent."
        )
    return identity


def build_location_random_slope_scale_certificate(
    result: LocationRandomSlopeScaleResult,
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


def validate_location_random_slope_scale_certificate(
    certificate: dict[str, Any],
) -> None:
    """Fail closed on certificate tampering or scientific-claim promotion."""
    require_exact_mapping_keys(
        certificate,
        CERTIFICATE_FIELDS,
        context="Location random-slope scale certificate",
    )
    if certificate.get("schema") != _CERTIFICATE_SCHEMA:
        raise SchemaError("Unsupported location random-slope scale certificate schema.")
    fingerprint = certificate.get("certificate_fingerprint_sha256")
    body = {
        key: value
        for key, value in certificate.items()
        if key != "certificate_fingerprint_sha256"
    }
    if not _is_sha256_hex(fingerprint) or fingerprint != benchmark_fingerprint(body):
        raise SchemaError("Location random-slope scale certificate fingerprint mismatch.")
    if certificate.get("claim_boundary") != _CLAIM_BOUNDARY:
        raise SchemaError("Location random-slope scale scientific claim boundary was altered.")
    require_canonical_optimizer(
        certificate.get("optimizer"),
        context="location random-slope scale",
    )
    model = certificate.get("model")
    required_model_fields = (
        "spec",
        "location_fixed_effects",
        "scale_fixed_effects",
        "tau_location_intercept",
        "tau_location_slope",
        "tau_log_scale",
        "population_random_effect_correlations",
        "log_likelihood",
        "n_obs",
        "n_groups",
        "group_effects_fingerprint_sha256",
        "input_fingerprint_sha256",
    )
    require_exact_mapping_keys(
        model,
        required_model_fields,
        context="Location random-slope scale model payload",
    )
    model_fingerprint = certificate.get("model_fingerprint_sha256")
    if (
        not _is_sha256_hex(model_fingerprint)
        or model_fingerprint != benchmark_fingerprint(model)
    ):
        raise SchemaError("Location random-slope scale model fingerprint mismatch.")
    try:
        canonical_spec = LocationRandomSlopeScaleSpec(**model["spec"])
    except (TypeError, ValueError) as exc:
        raise SchemaError(
            "Location random-slope scale certificate has an invalid model spec."
        ) from exc
    if benchmark_fingerprint(canonical_spec.to_dict()) != benchmark_fingerprint(
        model["spec"]
    ):
        raise SchemaError("Location random-slope scale certificate model spec is not canonical.")
    expected_location_terms = {"Intercept", *canonical_spec.location_predictors}
    expected_scale_terms = {"Intercept", *canonical_spec.scale_predictors}
    location_effects = model["location_fixed_effects"]
    scale_effects = model["scale_fixed_effects"]
    if not isinstance(location_effects, dict) or set(location_effects) != expected_location_terms:
        raise SchemaError("Location fixed-effect terms do not match the certified model spec.")
    if not isinstance(scale_effects, dict) or set(scale_effects) != expected_scale_terms:
        raise SchemaError("Scale fixed-effect terms do not match the certified model spec.")
    if model["population_random_effect_correlations"] != "independent":
        raise SchemaError("Population random-effect independence claim was altered.")
    if not _is_sha256_hex(model["group_effects_fingerprint_sha256"]):
        raise SchemaError("Group-effects fingerprint is invalid.")
    if not _is_sha256_hex(model["input_fingerprint_sha256"]):
        raise SchemaError("Input fingerprint is invalid.")
    numeric = [
        model["tau_location_intercept"],
        model["tau_location_slope"],
        model["tau_log_scale"],
        model["log_likelihood"],
        *location_effects.values(),
        *scale_effects.values(),
    ]
    require_finite_json_numbers(
        numeric,
        context="Location random-slope scale certificate estimates",
    )
    tau_intercept = float(model["tau_location_intercept"])
    tau_slope = float(model["tau_location_slope"])
    tau_scale = float(model["tau_log_scale"])
    if tau_intercept <= 0.0 or tau_slope <= 0.0 or tau_scale <= 0.0:
        raise SchemaError("Random-effect standard deviations must be positive.")
    if _random_effect_sd_boundary_reached(tau_intercept, tau_slope, tau_scale):
        raise SchemaError(
            "Certified random-effect standard deviation is at an artificial "
            "numerical boundary."
        )
    n_obs = model["n_obs"]
    n_groups = model["n_groups"]
    if not isinstance(n_obs, int) or isinstance(n_obs, bool) or n_obs <= 0:
        raise SchemaError("n_obs must be a positive integer.")
    if not isinstance(n_groups, int) or isinstance(n_groups, bool) or n_groups < 2:
        raise SchemaError("n_groups must be an integer of at least two.")
    if n_obs < n_groups * canonical_spec.min_group_size:
        raise SchemaError("Certified group/sample counts violate min_group_size.")


def freeze_location_random_slope_scale_certificate(
    result: LocationRandomSlopeScaleResult,
    path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Validate and freeze a certificate; protect existing files by default."""
    certificate = build_location_random_slope_scale_certificate(result)
    validate_location_random_slope_scale_certificate(certificate)
    target = Path(path)
    if target.exists() and not overwrite:
        raise FileExistsError(
            f"Location random-slope scale certificate already exists: {target}"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            certificate,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )
    return target
