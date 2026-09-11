"""Hierarchical Gaussian location-scale models for repeated eye-tracking outcomes."""

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

from .benchmarks import benchmark_fingerprint
from .exceptions import SchemaError
from .provenance import fingerprint_frame

_CERTIFICATE_SCHEMA = "gazeforge.hierarchical-location-scale-certificate.v1"
_LOG_2PI = float(np.log(2.0 * np.pi))
_CLAIM_BOUNDARY = {
    "joint_location_scale_model": True,
    "participant_random_location_intercept": True,
    "participant_random_log_scale_intercept": True,
    "adaptive_gauss_hermite_quadrature": True,
    "random_effect_correlation_modelled": False,
    "gaussian_conditional_outcome": True,
    "fixed_effect_p_values_provided": False,
    "causal_effects_established": False,
    "device_validity_established": False,
    "measurement_validity_established": False,
    "unseen_group_effects_known": False,
}


@dataclass(frozen=True, slots=True)
class HierarchicalLocationScaleSpec:
    """Specification for a Gaussian participant-level location-scale model.

    The conditional model is ``y_i ~ Normal(mu_i, sigma_i)`` with
    ``mu_i = X_i beta + b_g`` and ``log(sigma_i) = Z_i gamma + c_g``.
    Participant random intercepts ``b_g`` and ``c_g`` are independent
    zero-mean Gaussian terms. Their standard deviations are estimated jointly
    with the fixed effects by marginal maximum likelihood using two-dimensional
    adaptive Gauss-Hermite quadrature.

    Predictors must already be numeric. Coding, transformations, interactions,
    and centring remain explicit analysis-protocol decisions.
    """

    outcome_col: str
    group_col: str
    location_predictors: tuple[str, ...] = ()
    scale_predictors: tuple[str, ...] = ()
    quadrature_points: int = 5
    min_group_size: int = 3
    max_iter: int = 400
    tolerance: float = 1e-8

    def __post_init__(self) -> None:
        for name, value in (
            ("outcome_col", self.outcome_col),
            ("group_col", self.group_col),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string.")
            object.__setattr__(self, name, value.strip())
        if self.outcome_col == self.group_col:
            raise ValueError("outcome_col and group_col must be distinct columns.")
        location = _canonical_predictor_names(
            self.location_predictors, "location_predictors"
        )
        scale = _canonical_predictor_names(self.scale_predictors, "scale_predictors")
        collisions = sorted(
            (set(location) | set(scale)) & {self.outcome_col, self.group_col}
        )
        if collisions:
            raise ValueError(
                "Outcome/group columns cannot also be model predictors: "
                f"{collisions}"
            )
        q = int(self.quadrature_points)
        if q < 3 or q > 15 or q % 2 == 0:
            raise ValueError(
                "quadrature_points must be an odd integer from 3 through 15."
            )
        min_group_size = int(self.min_group_size)
        if min_group_size < 2:
            raise ValueError("min_group_size must be at least 2.")
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
class HierarchicalLocationScaleResult:
    """Fitted model and empirical-Bayes participant-effect summaries."""

    spec: HierarchicalLocationScaleSpec
    location_terms: tuple[str, ...]
    scale_terms: tuple[str, ...]
    location_coef: np.ndarray
    scale_coef: np.ndarray
    tau_location: float
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
        """Return location effects and scale effects on conditional sigma."""
        _validate_result_identity(self)
        rows: list[dict[str, Any]] = []
        for term, estimate in zip(
            self.location_terms, self.location_coef, strict=True
        ):
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
    group_levels: tuple[Any, ...]
    group_rows: tuple[np.ndarray, ...]
    location_terms: tuple[str, ...]
    scale_terms: tuple[str, ...]


def _canonical_predictor_names(
    values: tuple[str, ...], name: str
) -> tuple[str, ...]:
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
        raise SchemaError(
            f"Missing columns for hierarchical location-scale model: {missing}"
        )


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
        values = pd.to_numeric(
            data[predictor], errors="coerce"
        ).to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise SchemaError(
                f"{equation} predictor '{predictor}' must be finite and numeric."
            )
        columns.append(values)
        terms.append(predictor)
    design = np.column_stack(columns)
    if check_rank and np.linalg.matrix_rank(design) < design.shape[1]:
        raise SchemaError(f"{equation} design matrix is rank deficient.")
    return design, tuple(terms)


def _prepare_model(
    data: pd.DataFrame, spec: HierarchicalLocationScaleSpec
) -> _PreparedModel:
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data must be a pandas DataFrame.")
    if data.empty:
        raise SchemaError(
            "Hierarchical location-scale fitting requires at least one row."
        )
    required = (
        spec.outcome_col,
        spec.group_col,
        *spec.location_predictors,
        *spec.scale_predictors,
    )
    _require_columns(data, required)
    if data[spec.group_col].isna().any():
        raise SchemaError(
            "group_col must be complete; missing group identity is not allowed."
        )
    y = pd.to_numeric(data[spec.outcome_col], errors="coerce").to_numpy(
        dtype=float
    )
    if not np.isfinite(y).all():
        raise SchemaError("Outcome values must be finite and numeric.")
    location_design, location_terms = _numeric_design(
        data, spec.location_predictors, equation="Location"
    )
    scale_design, scale_terms = _numeric_design(
        data, spec.scale_predictors, equation="Scale"
    )
    group_codes, levels = pd.factorize(data[spec.group_col], sort=False)
    n_groups = len(levels)
    if n_groups < 2:
        raise SchemaError("Hierarchical fitting requires at least two groups.")
    sizes = np.bincount(group_codes, minlength=n_groups)
    too_small = np.flatnonzero(sizes < spec.min_group_size)
    if len(too_small):
        labels = [levels[index] for index in too_small[:10]]
        raise SchemaError(
            f"Every group needs at least {spec.min_group_size} observations; "
            f"undersized groups include {labels}."
        )
    group_rows = tuple(
        np.flatnonzero(group_codes == index) for index in range(n_groups)
    )
    return _PreparedModel(
        y=y,
        location_design=location_design,
        scale_design=scale_design,
        group_levels=tuple(levels.tolist()),
        group_rows=group_rows,
        location_terms=location_terms,
        scale_terms=scale_terms,
    )


def _initial_parameters(prepared: _PreparedModel) -> np.ndarray:
    beta = np.linalg.lstsq(
        prepared.location_design, prepared.y, rcond=None
    )[0]
    residual = prepared.y - prepared.location_design @ beta
    residual_sd = max(float(np.std(residual, ddof=1)), 1e-3)
    gamma = np.zeros(prepared.scale_design.shape[1], dtype=float)
    gamma[0] = np.log(residual_sd)
    group_means = np.array(
        [np.mean(residual[rows]) for rows in prepared.group_rows]
    )
    tau_location = max(
        float(np.std(group_means, ddof=1)), residual_sd * 0.05, 1e-3
    )
    relative_log_scales = []
    for rows in prepared.group_rows:
        group_sd = max(float(np.std(residual[rows], ddof=1)), 1e-3)
        relative_log_scales.append(
            np.log(group_sd) - np.log(residual_sd)
        )
    tau_scale = max(float(np.std(relative_log_scales, ddof=1)), 0.05)
    return np.concatenate(
        [beta, gamma, [np.log(tau_location), np.log(tau_scale)]]
    )


def _quadrature(
    spec: HierarchicalLocationScaleSpec,
) -> tuple[np.ndarray, np.ndarray]:
    nodes, weights = hermgauss(spec.quadrature_points)
    log_weight_grid = (
        np.log(weights)[:, None] + np.log(weights)[None, :]
    ).ravel()
    return nodes, log_weight_grid


def _unpack(
    theta: np.ndarray, n_location: int, n_scale: int
) -> tuple[np.ndarray, np.ndarray, float, float]:
    beta = theta[:n_location]
    gamma = theta[n_location : n_location + n_scale]
    tau_location = float(np.exp(theta[-2]))
    tau_scale = float(np.exp(theta[-1]))
    return beta, gamma, tau_location, tau_scale


def _group_log_integrand(
    random_effects: np.ndarray,
    y: np.ndarray,
    location_design: np.ndarray,
    scale_design: np.ndarray,
    beta: np.ndarray,
    gamma: np.ndarray,
    tau_location: float,
    tau_scale: float,
) -> tuple[float, np.ndarray, np.ndarray]:
    location_effect, scale_effect = random_effects
    residual = y - (location_design @ beta + location_effect)
    log_scale = scale_design @ gamma + scale_effect
    if np.any((log_scale < -25.0) | (log_scale > 25.0)):
        return -np.inf, np.zeros(2, dtype=float), np.eye(2, dtype=float)
    inverse_variance = np.exp(-2.0 * log_scale)
    log_value = float(
        np.sum(
            -0.5 * _LOG_2PI
            - log_scale
            - 0.5 * residual**2 * inverse_variance
        )
        - 0.5 * _LOG_2PI
        - np.log(tau_location)
        - 0.5 * (location_effect / tau_location) ** 2
        - 0.5 * _LOG_2PI
        - np.log(tau_scale)
        - 0.5 * (scale_effect / tau_scale) ** 2
    )
    gradient = np.array(
        [
            np.sum(residual * inverse_variance)
            - location_effect / tau_location**2,
            np.sum(-1.0 + residual**2 * inverse_variance)
            - scale_effect / tau_scale**2,
        ],
        dtype=float,
    )
    negative_hessian = np.array(
        [
            [
                np.sum(inverse_variance) + 1.0 / tau_location**2,
                2.0 * np.sum(residual * inverse_variance),
            ],
            [
                2.0 * np.sum(residual * inverse_variance),
                2.0 * np.sum(residual**2 * inverse_variance)
                + 1.0 / tau_scale**2,
            ],
        ],
        dtype=float,
    )
    return log_value, gradient, negative_hessian


def _adaptive_group_quadrature(
    y: np.ndarray,
    location_design: np.ndarray,
    scale_design: np.ndarray,
    beta: np.ndarray,
    gamma: np.ndarray,
    tau_location: float,
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
            beta,
            gamma,
            tau_location,
            tau_scale,
        )
        return 1e100 if not np.isfinite(value) else -value

    def negative_gradient(random_effects: np.ndarray) -> np.ndarray:
        value, gradient, _ = _group_log_integrand(
            random_effects,
            y,
            location_design,
            scale_design,
            beta,
            gamma,
            tau_location,
            tau_scale,
        )
        if not np.isfinite(value):
            return np.zeros(2, dtype=float)
        return -gradient

    mode_result = minimize(
        negative_log_posterior,
        np.zeros(2, dtype=float),
        jac=negative_gradient,
        method="BFGS",
        options={"gtol": 1e-8, "maxiter": 100},
    )
    mode = np.asarray(mode_result.x, dtype=float)
    mode_value, mode_gradient, negative_hessian = _group_log_integrand(
        mode,
        y,
        location_design,
        scale_design,
        beta,
        gamma,
        tau_location,
        tau_scale,
    )
    if (
        not np.isfinite(mode_value)
        or not np.isfinite(mode).all()
        or not np.isfinite(negative_hessian).all()
        or (
            not mode_result.success
            and np.linalg.norm(mode_gradient) > 1e-5
        )
    ):
        return -np.inf, np.empty((0, 2)), np.empty(0), mode
    sign, log_determinant = np.linalg.slogdet(negative_hessian)
    if sign <= 0:
        return -np.inf, np.empty((0, 2)), np.empty(0), mode
    try:
        cholesky = np.linalg.cholesky(negative_hessian)
    except np.linalg.LinAlgError:
        return -np.inf, np.empty((0, 2)), np.empty(0), mode
    inverse_root = np.linalg.inv(cholesky.T)
    node_pairs = np.array(
        [(first, second) for first in nodes for second in nodes],
        dtype=float,
    )
    random_effect_grid = mode[None, :] + np.sqrt(2.0) * (
        node_pairs @ inverse_root.T
    )
    adjusted_log_values = np.empty(len(node_pairs), dtype=float)
    for index, (random_effects, node_pair) in enumerate(
        zip(random_effect_grid, node_pairs, strict=True)
    ):
        value, _, _ = _group_log_integrand(
            random_effects,
            y,
            location_design,
            scale_design,
            beta,
            gamma,
            tau_location,
            tau_scale,
        )
        adjusted_log_values[index] = value + float(node_pair @ node_pair)
    weighted = log_weight_grid + adjusted_log_values
    log_normalizer = float(logsumexp(weighted))
    if not np.isfinite(log_normalizer):
        return -np.inf, np.empty((0, 2)), np.empty(0), mode
    log_integral = float(
        np.log(2.0) - 0.5 * log_determinant + log_normalizer
    )
    probabilities = np.exp(weighted - log_normalizer)
    if (
        not np.isfinite(probabilities).all()
        or not np.isclose(probabilities.sum(), 1.0)
    ):
        return -np.inf, np.empty((0, 2)), np.empty(0), mode
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
        beta, gamma, tau_location, tau_scale = _unpack(
            theta, n_location, n_scale
        )
        if (
            not np.isfinite(tau_location)
            or not np.isfinite(tau_scale)
            or tau_location < 1e-8
            or tau_scale < 1e-8
            or tau_location > 1e8
            or tau_scale > 20.0
        ):
            return 1e100
        total = 0.0
        for rows in prepared.group_rows:
            group_log_likelihood, _, _, _ = _adaptive_group_quadrature(
                prepared.y[rows],
                prepared.location_design[rows],
                prepared.scale_design[rows],
                beta,
                gamma,
                tau_location,
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
    spec: HierarchicalLocationScaleSpec,
    beta: np.ndarray,
    gamma: np.ndarray,
    tau_location: float,
    tau_scale: float,
    nodes: np.ndarray,
    log_weight_grid: np.ndarray,
) -> pd.DataFrame:
    rows_out: list[dict[str, Any]] = []
    for group_value, rows in zip(
        prepared.group_levels, prepared.group_rows, strict=True
    ):
        _, random_effect_grid, probabilities, mode = (
            _adaptive_group_quadrature(
                prepared.y[rows],
                prepared.location_design[rows],
                prepared.scale_design[rows],
                beta,
                gamma,
                tau_location,
                tau_scale,
                nodes,
                log_weight_grid,
            )
        )
        if len(probabilities) == 0:
            raise RuntimeError(
                "Adaptive quadrature failed while recovering group effects "
                f"for {group_value!r}."
            )
        location_values = random_effect_grid[:, 0]
        scale_values = random_effect_grid[:, 1]
        location_mean = float(probabilities @ location_values)
        scale_mean = float(probabilities @ scale_values)
        rows_out.append(
            {
                spec.group_col: group_value,
                "n_obs": int(len(rows)),
                "location_random_mode": float(mode[0]),
                "log_scale_random_mode": float(mode[1]),
                "location_random_mean": location_mean,
                "location_random_sd": float(
                    np.sqrt(
                        max(
                            probabilities
                            @ (location_values - location_mean) ** 2,
                            0.0,
                        )
                    )
                ),
                "log_scale_random_mean": scale_mean,
                "log_scale_random_sd": float(
                    np.sqrt(
                        max(
                            probabilities @ (scale_values - scale_mean) ** 2,
                            0.0,
                        )
                    )
                ),
                "scale_multiplier_mean": float(
                    probabilities @ np.exp(scale_values)
                ),
            }
        )
    return pd.DataFrame(rows_out)


def _model_identity_payload(
    *,
    spec: HierarchicalLocationScaleSpec,
    location_terms: tuple[str, ...],
    scale_terms: tuple[str, ...],
    location_coef: np.ndarray,
    scale_coef: np.ndarray,
    tau_location: float,
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
            term: float(value)
            for term, value in zip(
                location_terms, location_coef, strict=True
            )
        },
        "scale_fixed_effects": {
            term: float(value)
            for term, value in zip(scale_terms, scale_coef, strict=True)
        },
        "tau_location": float(tau_location),
        "tau_log_scale": float(tau_scale),
        "log_likelihood": float(log_likelihood),
        "n_obs": int(n_obs),
        "n_groups": int(n_groups),
        "group_effects_fingerprint_sha256": fingerprint_frame(group_effects),
        "input_fingerprint_sha256": input_fingerprint,
    }


def fit_hierarchical_location_scale(
    data: pd.DataFrame,
    *,
    spec: HierarchicalLocationScaleSpec,
    require_convergence: bool = True,
) -> HierarchicalLocationScaleResult:
    """Fit the joint marginal Gaussian location-scale model by AGHQ.

    The function does not compute fixed-effect p-values and does not transform
    observational coefficients into causal effects.
    """
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
            "Hierarchical location-scale optimizer did not converge: "
            f"{optimized.message}"
        )
    n_location = prepared.location_design.shape[1]
    n_scale = prepared.scale_design.shape[1]
    beta, gamma, tau_location, tau_scale = _unpack(
        optimized.x, n_location, n_scale
    )
    numeric = np.concatenate(
        [beta, gamma, [tau_location, tau_scale, float(optimized.fun)]]
    )
    if not np.isfinite(numeric).all():
        raise RuntimeError(
            "Hierarchical location-scale fit produced non-finite parameters."
        )
    group_effects = _posterior_group_effects(
        prepared,
        spec,
        beta,
        gamma,
        tau_location,
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
        tau_location=tau_location,
        tau_scale=tau_scale,
        log_likelihood=log_likelihood,
        n_obs=len(data),
        n_groups=len(prepared.group_levels),
        group_effects=group_effects,
        input_fingerprint=input_fingerprint,
    )
    return HierarchicalLocationScaleResult(
        spec=spec,
        location_terms=prepared.location_terms,
        scale_terms=prepared.scale_terms,
        location_coef=np.array(beta, dtype=float, copy=True),
        scale_coef=np.array(gamma, dtype=float, copy=True),
        tau_location=float(tau_location),
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


def predict_hierarchical_location_scale(
    result: HierarchicalLocationScaleResult,
    data: pd.DataFrame,
    *,
    include_group_effects: bool = True,
    allow_new_groups: bool = True,
) -> pd.DataFrame:
    """Predict conditional location and sigma.

    Known groups can use fitted empirical-Bayes effects. Unseen groups use the
    population-level prediction unless ``allow_new_groups=False``.
    """
    _validate_result_identity(result)
    spec = result.spec
    required = (
        spec.group_col,
        *spec.location_predictors,
        *spec.scale_predictors,
    )
    _require_columns(data, required)
    if data[spec.group_col].isna().any():
        raise SchemaError("Prediction group identities must be complete.")
    location_design, location_terms = _numeric_design(
        data,
        spec.location_predictors,
        equation="Location",
        check_rank=False,
    )
    scale_design, scale_terms = _numeric_design(
        data,
        spec.scale_predictors,
        equation="Scale",
        check_rank=False,
    )
    if (
        location_terms != result.location_terms
        or scale_terms != result.scale_terms
    ):
        raise RuntimeError(
            "Prediction design does not match the fitted model terms."
        )
    location = location_design @ result.location_coef
    log_scale = scale_design @ result.scale_coef
    effects_used = np.zeros(len(data), dtype=bool)
    if include_group_effects:
        effect_table = result.group_effects.set_index(spec.group_col)
        known = data[spec.group_col].isin(effect_table.index).to_numpy(
            dtype=bool
        )
        if not allow_new_groups and not known.all():
            unseen = (
                data.loc[~known, spec.group_col]
                .drop_duplicates()
                .tolist()[:10]
            )
            raise SchemaError(f"Prediction contains unseen groups: {unseen}")
        if np.any(known):
            group_values = data.loc[known, spec.group_col]
            location[known] += effect_table.loc[
                group_values, "location_random_mean"
            ].to_numpy(float)
            log_scale[known] += effect_table.loc[
                group_values, "log_scale_random_mean"
            ].to_numpy(float)
            effects_used[known] = True
    if np.any((log_scale < -25.0) | (log_scale > 25.0)):
        raise RuntimeError(
            "Predicted log-scale is outside the numerically supported range "
            "[-25, 25]."
        )
    output = pd.DataFrame(index=data.index)
    output["location_mean"] = location
    output["log_scale"] = log_scale
    output["sigma"] = np.exp(log_scale)
    output["group_effect_used"] = effects_used
    return output


def hierarchical_location_scale_diagnostics(
    result: HierarchicalLocationScaleResult,
    data: pd.DataFrame,
) -> pd.DataFrame:
    """Return fitted values and residual diagnostics without inferential tests."""
    _require_columns(data, (result.spec.outcome_col,))
    predicted = predict_hierarchical_location_scale(result, data)
    outcome = pd.to_numeric(
        data[result.spec.outcome_col], errors="coerce"
    ).to_numpy(dtype=float)
    if not np.isfinite(outcome).all():
        raise SchemaError("Outcome values must be finite for diagnostics.")
    residual = outcome - predicted["location_mean"].to_numpy(float)
    output = predicted.copy()
    output["residual"] = residual
    output["standardized_residual"] = (
        residual / predicted["sigma"].to_numpy(float)
    )
    return output


def _current_result_identity(
    result: HierarchicalLocationScaleResult,
) -> dict[str, Any]:
    return _model_identity_payload(
        spec=result.spec,
        location_terms=result.location_terms,
        scale_terms=result.scale_terms,
        location_coef=result.location_coef,
        scale_coef=result.scale_coef,
        tau_location=result.tau_location,
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
        and all(
            character in "0123456789abcdef" for character in value
        )
    )


def _validate_result_identity(
    result: HierarchicalLocationScaleResult,
) -> dict[str, Any]:
    identity = _current_result_identity(result)
    expected = benchmark_fingerprint(identity)
    if (
        not _is_sha256_hex(result.model_fingerprint_sha256)
        or result.model_fingerprint_sha256 != expected
    ):
        raise SchemaError(
            "Hierarchical location-scale result identity no longer matches "
            "the fitted model."
        )
    if not _is_sha256_hex(result.input_fingerprint_sha256):
        raise SchemaError(
            "Hierarchical location-scale input fingerprint is invalid."
        )
    if result.n_obs < result.n_groups * result.spec.min_group_size:
        raise SchemaError(
            "Hierarchical location-scale result group/sample counts are "
            "inconsistent."
        )
    return identity


def build_hierarchical_location_scale_certificate(
    result: HierarchicalLocationScaleResult,
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
    return {
        **body,
        "certificate_fingerprint_sha256": benchmark_fingerprint(body),
    }


def validate_hierarchical_location_scale_certificate(
    certificate: dict[str, Any],
) -> None:
    """Fail closed on certificate tampering or scientific-claim promotion."""
    if certificate.get("schema") != _CERTIFICATE_SCHEMA:
        raise SchemaError(
            "Unsupported hierarchical location-scale certificate schema."
        )
    fingerprint = certificate.get("certificate_fingerprint_sha256")
    body = {
        key: value
        for key, value in certificate.items()
        if key != "certificate_fingerprint_sha256"
    }
    if (
        not _is_sha256_hex(fingerprint)
        or fingerprint != benchmark_fingerprint(body)
    ):
        raise SchemaError(
            "Hierarchical location-scale certificate fingerprint mismatch."
        )
    if certificate.get("claim_boundary") != _CLAIM_BOUNDARY:
        raise SchemaError(
            "Hierarchical location-scale scientific claim boundary was altered."
        )
    optimizer = certificate.get("optimizer", {})
    if optimizer.get("converged") is not True:
        raise SchemaError(
            "Only converged hierarchical location-scale fits are certifiable."
        )
    if int(optimizer.get("iterations", -1)) < 0:
        raise SchemaError(
            "Hierarchical location-scale optimizer metadata are invalid."
        )
    model = certificate.get("model", {})
    required_model_fields = (
        "spec",
        "location_fixed_effects",
        "scale_fixed_effects",
        "tau_location",
        "tau_log_scale",
        "log_likelihood",
        "n_obs",
        "n_groups",
        "group_effects_fingerprint_sha256",
        "input_fingerprint_sha256",
    )
    for key in required_model_fields:
        if key not in model:
            raise SchemaError(
                "Hierarchical location-scale certificate is missing "
                f"model.{key}."
            )
    model_fingerprint = certificate.get("model_fingerprint_sha256")
    if (
        not _is_sha256_hex(model_fingerprint)
        or model_fingerprint != benchmark_fingerprint(model)
    ):
        raise SchemaError(
            "Hierarchical location-scale model fingerprint mismatch."
        )
    try:
        canonical_spec = HierarchicalLocationScaleSpec(**model["spec"])
    except (TypeError, ValueError) as exc:
        raise SchemaError(
            "Hierarchical location-scale certificate has an invalid model spec."
        ) from exc
    if benchmark_fingerprint(
        canonical_spec.to_dict()
    ) != benchmark_fingerprint(model["spec"]):
        raise SchemaError(
            "Hierarchical location-scale certificate model spec is not "
            "canonical."
        )
    expected_location_terms = {
        "Intercept",
        *canonical_spec.location_predictors,
    }
    expected_scale_terms = {"Intercept", *canonical_spec.scale_predictors}
    location_effects = model["location_fixed_effects"]
    scale_effects = model["scale_fixed_effects"]
    if not isinstance(location_effects, dict) or set(location_effects) != expected_location_terms:
        raise SchemaError(
            "Location fixed-effect terms do not match the certified model spec."
        )
    if not isinstance(scale_effects, dict) or set(scale_effects) != expected_scale_terms:
        raise SchemaError(
            "Scale fixed-effect terms do not match the certified model spec."
        )
    if not _is_sha256_hex(model["group_effects_fingerprint_sha256"]):
        raise SchemaError("Group-effects fingerprint is invalid.")
    if not _is_sha256_hex(model["input_fingerprint_sha256"]):
        raise SchemaError("Input fingerprint is invalid.")
    numeric = [
        model["tau_location"],
        model["tau_log_scale"],
        model["log_likelihood"],
        *location_effects.values(),
        *scale_effects.values(),
    ]
    if not np.isfinite(np.asarray(numeric, dtype=float)).all():
        raise SchemaError(
            "Hierarchical location-scale certificate contains non-finite "
            "estimates."
        )
    if (
        float(model["tau_location"]) <= 0
        or float(model["tau_log_scale"]) <= 0
    ):
        raise SchemaError(
            "Random-effect standard deviations must be positive."
        )
    n_obs = model["n_obs"]
    n_groups = model["n_groups"]
    if (
        not isinstance(n_obs, int)
        or isinstance(n_obs, bool)
        or n_obs <= 0
    ):
        raise SchemaError("n_obs must be a positive integer.")
    if (
        not isinstance(n_groups, int)
        or isinstance(n_groups, bool)
        or n_groups < 2
    ):
        raise SchemaError("n_groups must be an integer of at least two.")
    if n_obs < n_groups * canonical_spec.min_group_size:
        raise SchemaError(
            "Certified group/sample counts violate min_group_size."
        )


def freeze_hierarchical_location_scale_certificate(
    result: HierarchicalLocationScaleResult,
    path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Validate and freeze a certificate; protect existing files by default."""
    certificate = build_hierarchical_location_scale_certificate(result)
    validate_hierarchical_location_scale_certificate(certificate)
    target = Path(path)
    if target.exists() and not overwrite:
        raise FileExistsError(
            "Hierarchical location-scale certificate already exists: "
            f"{target}"
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
