"""Full 3x3 participant random-effects covariance Gaussian location-scale model."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
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
from .location_random_slope_scale import (
    _MAX_LOCATION_RANDOM_EFFECT_SD,
    _MAX_LOG_SCALE_RANDOM_EFFECT_SD,
    _MIN_RANDOM_EFFECT_SD,
    _node_triples,
    _numeric_design,
    _prepare_model,
    _quadrature,
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

_CERTIFICATE_SCHEMA = "gazeforge.full-covariance-location-random-slope-scale-certificate.v1"
_MAX_ABS_CORRELATION_ETA = 4.0
_CORRELATION_ETA_BOUNDARY_ATOL = 1e-6
_MAX_ABS_CERTIFIABLE_CORRELATION_COORDINATE = float(
    np.tanh(_MAX_ABS_CORRELATION_ETA - _CORRELATION_ETA_BOUNDARY_ATOL)
)
_MIN_CORRELATION_CHOLESKY_DIAGONAL = 1e-4
_LOG_2PI = float(np.log(2.0 * np.pi))
_LOG_2 = float(np.log(2.0))

_CLAIM_BOUNDARY = {
    "joint_location_scale_model": True,
    "participant_random_location_intercept": True,
    "participant_random_location_slope": True,
    "participant_random_log_scale_intercept": True,
    "full_three_by_three_random_effect_covariance_modelled": True,
    "location_intercept_slope_correlation_modelled": True,
    "location_intercept_log_scale_correlation_modelled": True,
    "location_slope_log_scale_correlation_modelled": True,
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
    "residual_calibration_supported_by_this_module": False,
    "hierarchical_bootstrap_supported_by_this_module": False,
}


@dataclass(frozen=True, slots=True)
class FullCovarianceLocationRandomSlopeScaleSpec:
    """Specification for a full 3x3 participant random-effects covariance model."""

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
class FullCovarianceLocationRandomSlopeScaleResult:
    """Fitted full-covariance model and empirical-Bayes participant summaries."""

    spec: FullCovarianceLocationRandomSlopeScaleSpec
    location_terms: tuple[str, ...]
    scale_terms: tuple[str, ...]
    location_coef: np.ndarray
    scale_coef: np.ndarray
    tau_location_intercept: float
    tau_location_slope: float
    tau_scale: float
    rho_location_intercept_slope: float
    rho_location_intercept_log_scale: float
    rho_location_slope_log_scale: float
    partial_rho_location_slope_log_scale_given_intercept: float
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

    def random_effect_correlation_matrix(self) -> np.ndarray:
        """Return the fitted population random-effects correlation matrix."""
        _validate_result_identity(self)
        return _correlation_matrix_from_coordinates(
            self.rho_location_intercept_slope,
            self.rho_location_intercept_log_scale,
            self.partial_rho_location_slope_log_scale_given_intercept,
        )[0]

    def random_effect_covariance_matrix(self) -> np.ndarray:
        """Return the fitted population random-effects covariance matrix."""
        _validate_result_identity(self)
        covariance, _, _, _ = _population_covariance(
            self.tau_location_intercept,
            self.tau_location_slope,
            self.tau_scale,
            self.rho_location_intercept_slope,
            self.rho_location_intercept_log_scale,
            self.partial_rho_location_slope_log_scale_given_intercept,
        )
        return covariance


def _initial_parameters(prepared: Any) -> np.ndarray:
    independent = _independent_initial_parameters(prepared)
    return np.concatenate([independent, np.zeros(3, dtype=float)])


def _correlation_matrix_from_etas(
    eta_intercept_slope: float,
    eta_intercept_scale: float,
    eta_slope_scale_given_intercept: float,
) -> tuple[np.ndarray, float, float, float, float]:
    r01 = float(np.tanh(eta_intercept_slope))
    r02 = float(np.tanh(eta_intercept_scale))
    partial = float(np.tanh(eta_slope_scale_given_intercept))
    matrix, r12 = _correlation_matrix_from_coordinates(r01, r02, partial)
    return matrix, r01, r02, r12, partial


def _correlation_matrix_from_coordinates(
    rho_intercept_slope: float,
    rho_intercept_scale: float,
    partial_rho_slope_scale_given_intercept: float,
) -> tuple[np.ndarray, float]:
    values = np.array(
        [
            rho_intercept_slope,
            rho_intercept_scale,
            partial_rho_slope_scale_given_intercept,
        ],
        dtype=float,
    )
    if not np.isfinite(values).all() or np.any(np.abs(values) >= 1.0):
        raise ValueError("Correlation coordinates must be finite and strictly inside (-1, 1).")
    r01, r02, partial = (float(value) for value in values)
    root01 = float(np.sqrt(max(1.0 - r01**2, 0.0)))
    root02 = float(np.sqrt(max(1.0 - r02**2, 0.0)))
    r12 = float(r01 * r02 + root01 * root02 * partial)
    matrix = np.array(
        [
            [1.0, r01, r02],
            [r01, 1.0, r12],
            [r02, r12, 1.0],
        ],
        dtype=float,
    )
    try:
        cholesky = np.linalg.cholesky(matrix)
    except np.linalg.LinAlgError as exc:
        raise ValueError("Random-effect correlation matrix is not positive definite.") from exc
    if (
        not np.isfinite(matrix).all()
        or not np.isfinite(cholesky).all()
        or float(np.min(np.diag(cholesky))) < _MIN_CORRELATION_CHOLESKY_DIAGONAL
    ):
        raise ValueError("Random-effect correlation matrix is numerically unsupported.")
    return matrix, r12


def _population_covariance(
    tau_intercept: float,
    tau_slope: float,
    tau_scale: float,
    rho_intercept_slope: float,
    rho_intercept_scale: float,
    partial_rho_slope_scale_given_intercept: float,
) -> tuple[np.ndarray, np.ndarray, float, float]:
    taus = np.array([tau_intercept, tau_slope, tau_scale], dtype=float)
    if not np.isfinite(taus).all() or np.any(taus <= 0.0):
        raise ValueError("Random-effect standard deviations must be finite and positive.")
    correlation, rho_slope_scale = _correlation_matrix_from_coordinates(
        rho_intercept_slope,
        rho_intercept_scale,
        partial_rho_slope_scale_given_intercept,
    )
    covariance = np.diag(taus) @ correlation @ np.diag(taus)
    sign, log_determinant = np.linalg.slogdet(covariance)
    if sign <= 0 or not np.isfinite(log_determinant):
        raise ValueError("Random-effect covariance matrix is numerically unsupported.")
    try:
        precision = np.linalg.inv(covariance)
    except np.linalg.LinAlgError as exc:
        raise ValueError("Random-effect covariance matrix is singular.") from exc
    if not np.isfinite(precision).all():
        raise ValueError("Random-effect covariance precision is non-finite.")
    return covariance, precision, float(log_determinant), rho_slope_scale


def _covariance_parameters_from_matrix(
    covariance: np.ndarray,
) -> tuple[float, float, float, float, float, float, float]:
    matrix = np.asarray(covariance, dtype=float)
    if matrix.shape != (3, 3) or not np.isfinite(matrix).all():
        raise ValueError("Random-effect covariance must be a finite 3x3 matrix.")
    if not np.allclose(matrix, matrix.T, rtol=0.0, atol=1e-12):
        raise ValueError("Random-effect covariance must be symmetric.")
    try:
        np.linalg.cholesky(matrix)
    except np.linalg.LinAlgError as exc:
        raise ValueError("Random-effect covariance must be positive definite.") from exc
    taus = np.sqrt(np.diag(matrix))
    correlation = matrix / np.outer(taus, taus)
    r01 = float(correlation[0, 1])
    r02 = float(correlation[0, 2])
    r12 = float(correlation[1, 2])
    denominator = float(np.sqrt((1.0 - r01**2) * (1.0 - r02**2)))
    if not np.isfinite(denominator) or denominator <= 0.0:
        raise ValueError("Random-effect covariance has unsupported correlation geometry.")
    partial = float((r12 - r01 * r02) / denominator)
    reconstructed, reconstructed_r12 = _correlation_matrix_from_coordinates(
        r01, r02, partial
    )
    if not np.allclose(correlation, reconstructed, rtol=1e-10, atol=1e-12):
        raise ValueError("Random-effect covariance correlation decomposition is unstable.")
    return (
        float(taus[0]),
        float(taus[1]),
        float(taus[2]),
        r01,
        r02,
        float(reconstructed_r12),
        partial,
    )


def transform_full_covariance_for_predictor_shift(
    covariance: np.ndarray,
    *,
    shift: float,
) -> np.ndarray:
    """Transform covariance when ``w_new = w_old - shift``."""
    if not isinstance(shift, (int, float, np.integer, np.floating)) or isinstance(
        shift, (bool, np.bool_)
    ):
        raise TypeError("shift must be a finite real number.")
    shift_value = float(shift)
    if not np.isfinite(shift_value):
        raise ValueError("shift must be finite.")
    matrix = np.asarray(covariance, dtype=float)
    _covariance_parameters_from_matrix(matrix)
    transform = np.array(
        [[1.0, shift_value, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        dtype=float,
    )
    shifted = transform @ matrix @ transform.T
    _covariance_parameters_from_matrix(shifted)
    return shifted


def _unpack(
    theta: np.ndarray,
    n_location: int,
    n_scale: int,
) -> tuple[
    np.ndarray,
    np.ndarray,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
]:
    beta = theta[:n_location]
    gamma = theta[n_location : n_location + n_scale]
    offset = n_location + n_scale
    tau_intercept = float(np.exp(theta[offset]))
    tau_slope = float(np.exp(theta[offset + 1]))
    tau_scale = float(np.exp(theta[offset + 2]))
    _, r01, r02, r12, partial = _correlation_matrix_from_etas(
        float(theta[offset + 3]),
        float(theta[offset + 4]),
        float(theta[offset + 5]),
    )
    return beta, gamma, tau_intercept, tau_slope, tau_scale, r01, r02, r12, partial


def _correlation_coordinate_at_numerical_boundary(value: float) -> bool:
    return not np.isfinite(value) or abs(value) >= _MAX_ABS_CERTIFIABLE_CORRELATION_COORDINATE


def _group_log_integrand(
    random_effects: np.ndarray,
    y: np.ndarray,
    location_design: np.ndarray,
    scale_design: np.ndarray,
    slope_values: np.ndarray,
    beta: np.ndarray,
    gamma: np.ndarray,
    precision: np.ndarray,
    covariance_log_determinant: float,
) -> tuple[float, np.ndarray, np.ndarray]:
    location_intercept, location_slope, scale_effect = random_effects
    residual = y - (
        location_design @ beta + location_intercept + location_slope * slope_values
    )
    log_scale = scale_design @ gamma + scale_effect
    if np.any((log_scale < -25.0) | (log_scale > 25.0)):
        return -np.inf, np.zeros(3, dtype=float), np.eye(3, dtype=float)
    inverse_variance = np.exp(-2.0 * log_scale)
    effects = np.asarray(random_effects, dtype=float)
    prior_quadratic = float(effects @ precision @ effects)
    log_value = float(
        np.sum(-0.5 * _LOG_2PI - log_scale - 0.5 * residual**2 * inverse_variance)
        - 1.5 * _LOG_2PI
        - 0.5 * covariance_log_determinant
        - 0.5 * prior_quadratic
    )
    weighted_residual = residual * inverse_variance
    likelihood_cross_intercept_scale = 2.0 * np.sum(weighted_residual)
    likelihood_cross_slope_scale = 2.0 * np.sum(slope_values * weighted_residual)
    likelihood_negative_hessian = np.array(
        [
            [
                np.sum(inverse_variance),
                np.sum(slope_values * inverse_variance),
                likelihood_cross_intercept_scale,
            ],
            [
                np.sum(slope_values * inverse_variance),
                np.sum(slope_values**2 * inverse_variance),
                likelihood_cross_slope_scale,
            ],
            [
                likelihood_cross_intercept_scale,
                likelihood_cross_slope_scale,
                2.0 * np.sum(residual**2 * inverse_variance),
            ],
        ],
        dtype=float,
    )
    likelihood_gradient = np.array(
        [
            np.sum(weighted_residual),
            np.sum(slope_values * weighted_residual),
            np.sum(-1.0 + residual**2 * inverse_variance),
        ],
        dtype=float,
    )
    gradient = likelihood_gradient - precision @ effects
    negative_hessian = likelihood_negative_hessian + precision
    return log_value, gradient, negative_hessian


def _adaptive_group_quadrature_full_covariance(
    y: np.ndarray,
    location_design: np.ndarray,
    scale_design: np.ndarray,
    slope_values: np.ndarray,
    beta: np.ndarray,
    gamma: np.ndarray,
    precision: np.ndarray,
    covariance_log_determinant: float,
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
            precision,
            covariance_log_determinant,
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
            precision,
            covariance_log_determinant,
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
            precision,
            covariance_log_determinant,
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
        precision,
        covariance_log_determinant,
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
            precision,
            covariance_log_determinant,
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


def _objective_factory(prepared: Any, nodes: np.ndarray, log_weight_grid: np.ndarray):
    n_location = prepared.location_design.shape[1]
    n_scale = prepared.scale_design.shape[1]

    def objective(theta: np.ndarray) -> float:
        if not np.isfinite(theta).all():
            return 1e100
        try:
            (
                beta,
                gamma,
                tau_intercept,
                tau_slope,
                tau_scale,
                r01,
                r02,
                _,
                partial,
            ) = _unpack(theta, n_location, n_scale)
            _, precision, covariance_log_determinant, _ = _population_covariance(
                tau_intercept,
                tau_slope,
                tau_scale,
                r01,
                r02,
                partial,
            )
        except ValueError:
            return 1e100
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
            group_log_likelihood, _, _, _ = _adaptive_group_quadrature_full_covariance(
                prepared.y[rows],
                prepared.location_design[rows],
                prepared.scale_design[rows],
                prepared.slope_values[rows],
                beta,
                gamma,
                precision,
                covariance_log_determinant,
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
    spec: FullCovarianceLocationRandomSlopeScaleSpec,
    beta: np.ndarray,
    gamma: np.ndarray,
    tau_intercept: float,
    tau_slope: float,
    tau_scale: float,
    r01: float,
    r02: float,
    partial: float,
    nodes: np.ndarray,
    log_weight_grid: np.ndarray,
) -> pd.DataFrame:
    _, precision, covariance_log_determinant, _ = _population_covariance(
        tau_intercept,
        tau_slope,
        tau_scale,
        r01,
        r02,
        partial,
    )
    rows_out: list[dict[str, Any]] = []
    for group_value, rows in zip(prepared.group_levels, prepared.group_rows, strict=True):
        _, grid, probabilities, mode = _adaptive_group_quadrature_full_covariance(
            prepared.y[rows],
            prepared.location_design[rows],
            prepared.scale_design[rows],
            prepared.slope_values[rows],
            beta,
            gamma,
            precision,
            covariance_log_determinant,
            nodes,
            log_weight_grid,
        )
        if len(probabilities) == 0:
            raise RuntimeError(
                "Adaptive quadrature failed while recovering full-covariance group "
                f"effects for {group_value!r}."
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
    spec: FullCovarianceLocationRandomSlopeScaleSpec,
    location_terms: tuple[str, ...],
    scale_terms: tuple[str, ...],
    location_coef: np.ndarray,
    scale_coef: np.ndarray,
    tau_intercept: float,
    tau_slope: float,
    tau_scale: float,
    rho_intercept_slope: float,
    rho_intercept_scale: float,
    rho_slope_scale: float,
    partial_rho_slope_scale_given_intercept: float,
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
        "rho_location_intercept_slope": float(rho_intercept_slope),
        "rho_location_intercept_log_scale": float(rho_intercept_scale),
        "rho_location_slope_log_scale": float(rho_slope_scale),
        "partial_rho_location_slope_log_scale_given_intercept": float(
            partial_rho_slope_scale_given_intercept
        ),
        "log_likelihood": float(log_likelihood),
        "n_obs": int(n_obs),
        "n_groups": int(n_groups),
        "group_effects_fingerprint_sha256": fingerprint_frame(group_effects),
        "input_fingerprint_sha256": input_fingerprint,
    }


def fit_full_covariance_location_random_slope_scale(
    data: pd.DataFrame,
    *,
    spec: FullCovarianceLocationRandomSlopeScaleSpec,
    require_convergence: bool = True,
) -> FullCovarianceLocationRandomSlopeScaleResult:
    """Fit the full 3x3 participant covariance model with 3D AGHQ."""
    prepared = _prepare_model(data, spec)
    initial = _initial_parameters(prepared)
    nodes, log_weight_grid = _quadrature(spec)
    objective = _objective_factory(prepared, nodes, log_weight_grid)
    bounds = [(None, None)] * (len(initial) - 3) + [
        (-_MAX_ABS_CORRELATION_ETA, _MAX_ABS_CORRELATION_ETA),
        (-_MAX_ABS_CORRELATION_ETA, _MAX_ABS_CORRELATION_ETA),
        (-_MAX_ABS_CORRELATION_ETA, _MAX_ABS_CORRELATION_ETA),
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
            "Full-covariance location random-slope scale optimizer did not converge: "
            f"{optimized.message}"
        )
    optimized_array = np.asarray(optimized.x, dtype=float)
    eta_coordinates = optimized_array[-3:]
    if (
        not np.isfinite(eta_coordinates).all()
        or np.any(
            np.abs(eta_coordinates)
            >= _MAX_ABS_CORRELATION_ETA - _CORRELATION_ETA_BOUNDARY_ATOL
        )
    ):
        raise RuntimeError(
            "Full-covariance random-effect correlation estimate reached an artificial "
            "optimizer bound and is not certifiable."
        )
    n_location = prepared.location_design.shape[1]
    n_scale = prepared.scale_design.shape[1]
    (
        beta,
        gamma,
        tau_intercept,
        tau_slope,
        tau_scale,
        r01,
        r02,
        r12,
        partial,
    ) = _unpack(optimized_array, n_location, n_scale)
    numeric = np.concatenate(
        [
            beta,
            gamma,
            [
                tau_intercept,
                tau_slope,
                tau_scale,
                r01,
                r02,
                r12,
                partial,
                float(optimized.fun),
            ],
        ]
    )
    if not np.isfinite(numeric).all():
        raise RuntimeError(
            "Full-covariance location random-slope scale fit produced non-finite parameters."
        )
    if _random_effect_sd_boundary_reached(tau_intercept, tau_slope, tau_scale):
        raise RuntimeError(
            "Full-covariance location random-slope scale random-effect standard deviation "
            "reached an artificial numerical boundary and is not certifiable."
        )
    try:
        _population_covariance(tau_intercept, tau_slope, tau_scale, r01, r02, partial)
    except ValueError as exc:
        raise RuntimeError(
            "Full-covariance random-effect covariance is numerically unsupported."
        ) from exc
    group_effects = _posterior_group_effects(
        prepared,
        spec,
        beta,
        gamma,
        tau_intercept,
        tau_slope,
        tau_scale,
        r01,
        r02,
        partial,
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
        rho_intercept_slope=r01,
        rho_intercept_scale=r02,
        rho_slope_scale=r12,
        partial_rho_slope_scale_given_intercept=partial,
        log_likelihood=log_likelihood,
        n_obs=len(data),
        n_groups=len(prepared.group_levels),
        group_effects=group_effects,
        input_fingerprint=input_fingerprint,
    )
    return FullCovarianceLocationRandomSlopeScaleResult(
        spec=spec,
        location_terms=prepared.location_terms,
        scale_terms=prepared.scale_terms,
        location_coef=np.array(beta, dtype=float, copy=True),
        scale_coef=np.array(gamma, dtype=float, copy=True),
        tau_location_intercept=float(tau_intercept),
        tau_location_slope=float(tau_slope),
        tau_scale=float(tau_scale),
        rho_location_intercept_slope=float(r01),
        rho_location_intercept_log_scale=float(r02),
        rho_location_slope_log_scale=float(r12),
        partial_rho_location_slope_log_scale_given_intercept=float(partial),
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


def predict_full_covariance_location_random_slope_scale(
    result: FullCovarianceLocationRandomSlopeScaleResult,
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


def full_covariance_location_random_slope_scale_diagnostics(
    result: FullCovarianceLocationRandomSlopeScaleResult,
    data: pd.DataFrame,
) -> pd.DataFrame:
    """Return fitted values and residual diagnostics without inferential tests."""
    _require_columns(data, (result.spec.outcome_col,))
    predicted = predict_full_covariance_location_random_slope_scale(result, data)
    outcome = pd.to_numeric(data[result.spec.outcome_col], errors="coerce").to_numpy(
        dtype=float
    )
    if not np.isfinite(outcome).all():
        raise SchemaError("Outcome values must be finite for diagnostics.")
    residual = outcome - predicted["location_mean"].to_numpy(float)
    output = predicted.copy()
    output["residual"] = residual
    output["standardized_residual"] = residual / predicted["sigma"].to_numpy(float)
    return output


def _current_result_identity(
    result: FullCovarianceLocationRandomSlopeScaleResult,
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
        rho_intercept_slope=result.rho_location_intercept_slope,
        rho_intercept_scale=result.rho_location_intercept_log_scale,
        rho_slope_scale=result.rho_location_slope_log_scale,
        partial_rho_slope_scale_given_intercept=(
            result.partial_rho_location_slope_log_scale_given_intercept
        ),
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


def _validate_correlation_coordinates(
    *,
    rho_intercept_slope: float,
    rho_intercept_scale: float,
    rho_slope_scale: float,
    partial_rho_slope_scale_given_intercept: float,
) -> None:
    for value in (
        rho_intercept_slope,
        rho_intercept_scale,
        partial_rho_slope_scale_given_intercept,
    ):
        if _correlation_coordinate_at_numerical_boundary(float(value)):
            raise SchemaError(
                "Full-covariance correlation coordinate is at the artificial optimizer "
                "boundary and is not certifiable."
            )
    try:
        correlation, reconstructed_r12 = _correlation_matrix_from_coordinates(
            float(rho_intercept_slope),
            float(rho_intercept_scale),
            float(partial_rho_slope_scale_given_intercept),
        )
    except ValueError as exc:
        raise SchemaError(
            "Full-covariance random-effect correlation matrix is numerically unsupported."
        ) from exc
    if not np.isclose(float(rho_slope_scale), reconstructed_r12, rtol=1e-10, atol=1e-12):
        raise SchemaError(
            "Marginal slope/log-scale correlation is inconsistent with the certified "
            "vine-partial correlation coordinates."
        )
    if not np.isfinite(correlation).all():
        raise SchemaError("Full-covariance random-effect correlation matrix is non-finite.")


def _validate_result_identity(
    result: FullCovarianceLocationRandomSlopeScaleResult,
) -> dict[str, Any]:
    identity = _current_result_identity(result)
    expected = benchmark_fingerprint(identity)
    if (
        not _is_sha256_hex(result.model_fingerprint_sha256)
        or result.model_fingerprint_sha256 != expected
    ):
        raise SchemaError(
            "Full-covariance location random-slope scale result identity no longer "
            "matches the fitted model."
        )
    if not _is_sha256_hex(result.input_fingerprint_sha256):
        raise SchemaError(
            "Full-covariance location random-slope scale input fingerprint is invalid."
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
            "Full-covariance random-effect standard deviation is at an artificial "
            "numerical boundary and is not certifiable."
        )
    _validate_correlation_coordinates(
        rho_intercept_slope=result.rho_location_intercept_slope,
        rho_intercept_scale=result.rho_location_intercept_log_scale,
        rho_slope_scale=result.rho_location_slope_log_scale,
        partial_rho_slope_scale_given_intercept=(
            result.partial_rho_location_slope_log_scale_given_intercept
        ),
    )
    try:
        _population_covariance(
            result.tau_location_intercept,
            result.tau_location_slope,
            result.tau_scale,
            result.rho_location_intercept_slope,
            result.rho_location_intercept_log_scale,
            result.partial_rho_location_slope_log_scale_given_intercept,
        )
    except ValueError as exc:
        raise SchemaError(
            "Full-covariance random-effect covariance is numerically unsupported."
        ) from exc
    if result.n_obs < result.n_groups * result.spec.min_group_size:
        raise SchemaError(
            "Full-covariance location random-slope scale result group/sample counts "
            "are inconsistent."
        )
    return identity


def build_full_covariance_location_random_slope_scale_certificate(
    result: FullCovarianceLocationRandomSlopeScaleResult,
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


def validate_full_covariance_location_random_slope_scale_certificate(
    certificate: dict[str, Any],
) -> None:
    """Fail closed on certificate tampering or scientific-claim promotion."""
    require_exact_mapping_keys(
        certificate,
        CERTIFICATE_FIELDS,
        context="Full-covariance location random-slope scale certificate",
    )
    if certificate.get("schema") != _CERTIFICATE_SCHEMA:
        raise SchemaError(
            "Unsupported full-covariance location random-slope scale certificate schema."
        )
    fingerprint = certificate.get("certificate_fingerprint_sha256")
    body = {
        key: value
        for key, value in certificate.items()
        if key != "certificate_fingerprint_sha256"
    }
    if not _is_sha256_hex(fingerprint) or fingerprint != benchmark_fingerprint(body):
        raise SchemaError(
            "Full-covariance location random-slope scale certificate fingerprint mismatch."
        )
    if certificate.get("claim_boundary") != _CLAIM_BOUNDARY:
        raise SchemaError(
            "Full-covariance location random-slope scale scientific claim boundary was altered."
        )
    require_canonical_optimizer(
        certificate.get("optimizer"),
        context="full-covariance location random-slope scale",
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
        "rho_location_intercept_log_scale",
        "rho_location_slope_log_scale",
        "partial_rho_location_slope_log_scale_given_intercept",
        "log_likelihood",
        "n_obs",
        "n_groups",
        "group_effects_fingerprint_sha256",
        "input_fingerprint_sha256",
    )
    require_exact_mapping_keys(
        model,
        required_model_fields,
        context="Full-covariance location random-slope scale model payload",
    )
    model_fingerprint = certificate.get("model_fingerprint_sha256")
    if (
        not _is_sha256_hex(model_fingerprint)
        or model_fingerprint != benchmark_fingerprint(model)
    ):
        raise SchemaError(
            "Full-covariance location random-slope scale model fingerprint mismatch."
        )
    try:
        canonical_spec = FullCovarianceLocationRandomSlopeScaleSpec(**model["spec"])
    except (TypeError, ValueError) as exc:
        raise SchemaError(
            "Full-covariance location random-slope scale certificate has an invalid model spec."
        ) from exc
    if benchmark_fingerprint(canonical_spec.to_dict()) != benchmark_fingerprint(
        model["spec"]
    ):
        raise SchemaError(
            "Full-covariance location random-slope scale certificate model spec is not canonical."
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
        model["rho_location_intercept_log_scale"],
        model["rho_location_slope_log_scale"],
        model["partial_rho_location_slope_log_scale_given_intercept"],
        model["log_likelihood"],
        *location_effects.values(),
        *scale_effects.values(),
    ]
    require_finite_json_numbers(
        numeric,
        context="Full-covariance location random-slope scale certificate estimates",
    )
    tau_intercept = float(model["tau_location_intercept"])
    tau_slope = float(model["tau_location_slope"])
    tau_scale = float(model["tau_log_scale"])
    if tau_intercept <= 0.0 or tau_slope <= 0.0 or tau_scale <= 0.0:
        raise SchemaError("Random-effect standard deviations must be positive.")
    if _random_effect_sd_boundary_reached(tau_intercept, tau_slope, tau_scale):
        raise SchemaError(
            "Certified random-effect standard deviation is at an artificial numerical boundary."
        )
    _validate_correlation_coordinates(
        rho_intercept_slope=float(model["rho_location_intercept_slope"]),
        rho_intercept_scale=float(model["rho_location_intercept_log_scale"]),
        rho_slope_scale=float(model["rho_location_slope_log_scale"]),
        partial_rho_slope_scale_given_intercept=float(
            model["partial_rho_location_slope_log_scale_given_intercept"]
        ),
    )
    try:
        _population_covariance(
            tau_intercept,
            tau_slope,
            tau_scale,
            float(model["rho_location_intercept_slope"]),
            float(model["rho_location_intercept_log_scale"]),
            float(model["partial_rho_location_slope_log_scale_given_intercept"]),
        )
    except ValueError as exc:
        raise SchemaError(
            "Certified random-effect covariance is numerically unsupported."
        ) from exc
    n_obs = model["n_obs"]
    n_groups = model["n_groups"]
    if not isinstance(n_obs, int) or isinstance(n_obs, bool) or n_obs <= 0:
        raise SchemaError("n_obs must be a positive integer.")
    if not isinstance(n_groups, int) or isinstance(n_groups, bool) or n_groups < 2:
        raise SchemaError("n_groups must be an integer of at least two.")
    if n_obs < n_groups * canonical_spec.min_group_size:
        raise SchemaError("Certified group/sample counts violate min_group_size.")


def freeze_full_covariance_location_random_slope_scale_certificate(
    result: FullCovarianceLocationRandomSlopeScaleResult,
    path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Validate and freeze a certificate; protect existing files by default."""
    certificate = build_full_covariance_location_random_slope_scale_certificate(result)
    validate_full_covariance_location_random_slope_scale_certificate(certificate)
    target = Path(path)
    if target.exists() and not overwrite:
        raise FileExistsError(
            "Full-covariance location random-slope scale certificate already exists: "
            f"{target}"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(certificate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target
