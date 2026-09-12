"""Simulation-calibrated residual diagnostics for location-scale models."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import norm

from ._certificate_schema import require_exact_mapping_keys
from .benchmarks import benchmark_fingerprint
from .correlated_location_scale import (
    CorrelatedLocationScaleResult,
    build_correlated_location_scale_certificate,
    correlated_location_scale_diagnostics,
    validate_correlated_location_scale_certificate,
)
from .exceptions import SchemaError
from .hierarchical_location_scale import (
    HierarchicalLocationScaleResult,
    build_hierarchical_location_scale_certificate,
    hierarchical_location_scale_diagnostics,
    validate_hierarchical_location_scale_certificate,
)
from .location_random_slope_scale import (
    LocationRandomSlopeScaleResult,
    build_location_random_slope_scale_certificate,
    location_random_slope_scale_diagnostics,
    validate_location_random_slope_scale_certificate,
)
from .provenance import fingerprint_frame

_CERTIFICATE_SCHEMA = "gazeforge.location-scale-residual-calibration-certificate.v1"
_DIAGNOSTIC_SCHEMA = "gazeforge.location-scale-residual-calibration.v1"
_SUPPORTED_MODEL_FAMILIES = frozenset(
    {
        "independent_location_scale",
        "correlated_location_scale",
        "location_random_slope_scale",
    }
)
LocationScaleModelResult = (
    HierarchicalLocationScaleResult
    | CorrelatedLocationScaleResult
    | LocationRandomSlopeScaleResult
)
_CERTIFICATE_FIELDS = frozenset(
    {
        "schema",
        "diagnostic",
        "diagnostic_fingerprint_sha256",
        "summary",
        "claim_boundary",
        "certificate_fingerprint_sha256",
    }
)
_DIAGNOSTIC_FIELDS = frozenset(
    {
        "schema",
        "spec",
        "model_family",
        "model_fingerprint_sha256",
        "base_model_certificate_fingerprint_sha256",
        "input_fingerprint_sha256",
        "n_obs",
        "n_groups",
        "residuals_fingerprint_sha256",
        "summary_fingerprint_sha256",
    }
)
_SUMMARY_COLUMNS = (
    "metric",
    "observed",
    "simulation_mean",
    "envelope_lower",
    "envelope_upper",
    "simulation_percentile",
    "outside_envelope",
)
_METRIC_ORDER = (
    "residual_mean",
    "residual_sd",
    "residual_skewness",
    "residual_excess_kurtosis",
    "absolute_tail_fraction",
    "normal_qq_rmse",
    "group_mean_rms",
    "group_log_second_moment_rms",
)
_CLAIM_BOUNDARY = {
    "conditional_residual_calibration_computed": True,
    "standard_normal_reference_simulated": True,
    "group_structure_preserved_in_reference_metrics": True,
    "exact_fitting_input_required": True,
    "certifiable_base_model_required": True,
    "model_parameters_refit_per_simulation": False,
    "parameter_uncertainty_propagated": False,
    "global_model_adequacy_established": False,
    "distributional_correctness_established": False,
    "causal_effects_established": False,
    "device_validity_established": False,
    "measurement_validity_established": False,
}


@dataclass(frozen=True, slots=True)
class LocationScaleResidualCalibrationSpec:
    """Specification for deterministic conditional residual calibration.

    The reference simulations draw standardized residuals from ``N(0, 1)``
    while preserving the fitted sample's row count and grouping structure.
    Model parameters and empirical-Bayes group effects are held fixed; they are
    not re-estimated in each simulation replicate.
    """

    n_simulations: int = 500
    seed: int = 1729
    envelope_level: float = 0.95
    absolute_tail_threshold: float = 1.96
    max_simulated_residual_draws: int = 5_000_000

    def __post_init__(self) -> None:
        if (
            not isinstance(self.n_simulations, int)
            or isinstance(self.n_simulations, bool)
            or self.n_simulations < 50
            or self.n_simulations > 100_000
        ):
            raise ValueError(
                "n_simulations must be an integer from 50 through 100000."
            )
        if not isinstance(self.seed, int) or isinstance(self.seed, bool) or self.seed < 0:
            raise ValueError("seed must be a non-negative integer.")
        level = float(self.envelope_level)
        if not np.isfinite(level) or not 0.5 < level < 1.0:
            raise ValueError("envelope_level must be finite and between 0.5 and 1.0.")
        threshold = float(self.absolute_tail_threshold)
        if not np.isfinite(threshold) or threshold <= 0:
            raise ValueError("absolute_tail_threshold must be finite and positive.")
        if (
            not isinstance(self.max_simulated_residual_draws, int)
            or isinstance(self.max_simulated_residual_draws, bool)
            or self.max_simulated_residual_draws < 1
        ):
            raise ValueError("max_simulated_residual_draws must be a positive integer.")
        object.__setattr__(self, "envelope_level", level)
        object.__setattr__(self, "absolute_tail_threshold", threshold)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the canonical diagnostic specification."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LocationScaleResidualCalibrationResult:
    """Simulation-calibrated conditional residual diagnostic result."""

    spec: LocationScaleResidualCalibrationSpec
    model_family: str
    model_fingerprint_sha256: str
    base_model_certificate_fingerprint_sha256: str
    input_fingerprint_sha256: str
    n_obs: int
    n_groups: int
    residuals_fingerprint_sha256: str
    summary: pd.DataFrame
    summary_fingerprint_sha256: str
    diagnostic_fingerprint_sha256: str

    def metrics(self) -> pd.DataFrame:
        """Return a defensive copy of the metric-envelope table."""
        _validate_result_identity(self)
        return self.summary.copy(deep=True)


def _is_sha256_hex(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _model_adapter(
    result: LocationScaleModelResult,
) -> tuple[str, Any, Any]:
    if isinstance(result, HierarchicalLocationScaleResult):
        return "independent_location_scale", result.spec, hierarchical_location_scale_diagnostics
    if isinstance(result, CorrelatedLocationScaleResult):
        return "correlated_location_scale", result.spec, correlated_location_scale_diagnostics
    if isinstance(result, LocationRandomSlopeScaleResult):
        return (
            "location_random_slope_scale",
            result.spec,
            location_random_slope_scale_diagnostics,
        )
    raise TypeError(
        "result must be a HierarchicalLocationScaleResult, "
        "CorrelatedLocationScaleResult, or LocationRandomSlopeScaleResult."
    )


def _require_certifiable_base_model(
    result: LocationScaleModelResult,
) -> str:
    if isinstance(result, HierarchicalLocationScaleResult):
        certificate = build_hierarchical_location_scale_certificate(result)
        validate_hierarchical_location_scale_certificate(certificate)
    elif isinstance(result, CorrelatedLocationScaleResult):
        certificate = build_correlated_location_scale_certificate(result)
        validate_correlated_location_scale_certificate(certificate)
    elif isinstance(result, LocationRandomSlopeScaleResult):
        certificate = build_location_random_slope_scale_certificate(result)
        validate_location_random_slope_scale_certificate(certificate)
    else:
        raise TypeError(
            "result must be a HierarchicalLocationScaleResult, "
            "CorrelatedLocationScaleResult, or LocationRandomSlopeScaleResult."
        )
    fingerprint = certificate.get("certificate_fingerprint_sha256")
    if not _is_sha256_hex(fingerprint):
        raise SchemaError("Base location-scale model certificate fingerprint is invalid.")
    return fingerprint


def _input_columns(spec: Any) -> list[str]:
    return list(
        dict.fromkeys(
            (
                spec.outcome_col,
                spec.group_col,
                *spec.location_predictors,
                *spec.scale_predictors,
            )
        )
    )


def _require_exact_fitting_input(result: Any, data: pd.DataFrame) -> str:
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data must be a pandas DataFrame.")
    columns = _input_columns(result.spec)
    missing = [column for column in columns if column not in data.columns]
    if missing:
        raise SchemaError(f"Residual calibration input is missing columns: {missing}")
    current = fingerprint_frame(data.loc[:, columns])
    if current != result.input_fingerprint_sha256:
        raise SchemaError(
            "Residual calibration requires the exact fitted modelling input; "
            "the supplied table fingerprint does not match the fitted result."
        )
    return current


def _safe_standardized_moments(z: np.ndarray) -> tuple[float, float, float, float]:
    mean = float(np.mean(z))
    if len(z) < 2:
        raise SchemaError("Residual calibration requires at least two observations.")
    sd = float(np.std(z, ddof=1))
    if not np.isfinite(sd) or sd <= 0:
        raise SchemaError("Standardized residuals must have non-zero finite dispersion.")
    centered = z - mean
    population_sd = float(np.sqrt(np.mean(centered**2)))
    skewness = float(np.mean(centered**3) / population_sd**3)
    excess_kurtosis = float(np.mean(centered**4) / population_sd**4 - 3.0)
    return mean, sd, skewness, excess_kurtosis


def _normal_qq_rmse(z: np.ndarray) -> float:
    ordered = np.sort(z)
    probabilities = (np.arange(len(z), dtype=float) + 0.5) / len(z)
    expected = norm.ppf(probabilities)
    return float(np.sqrt(np.mean((ordered - expected) ** 2)))


def _group_metric_arrays(
    z: np.ndarray,
    group_codes: np.ndarray,
    n_groups: int,
) -> tuple[np.ndarray, np.ndarray]:
    means = np.empty(n_groups, dtype=float)
    log_second_moments = np.empty(n_groups, dtype=float)
    for group_index in range(n_groups):
        values = z[group_codes == group_index]
        if len(values) == 0:
            raise SchemaError("Residual calibration encountered an empty group.")
        means[group_index] = float(np.mean(values))
        second_moment = float(np.mean(values**2))
        if second_moment <= 0 or not np.isfinite(second_moment):
            raise SchemaError("Group residual second moments must be finite and positive.")
        log_second_moments[group_index] = float(np.log(second_moment))
    return means, log_second_moments


def _residual_metrics(
    z: np.ndarray,
    group_codes: np.ndarray,
    n_groups: int,
    *,
    tail_threshold: float,
) -> dict[str, float]:
    z = np.asarray(z, dtype=float)
    if z.ndim != 1 or len(z) != len(group_codes) or not np.isfinite(z).all():
        raise SchemaError("Standardized residuals must be a finite one-dimensional vector.")
    mean, sd, skewness, excess_kurtosis = _safe_standardized_moments(z)
    group_means, group_log_second = _group_metric_arrays(z, group_codes, n_groups)
    return {
        "residual_mean": mean,
        "residual_sd": sd,
        "residual_skewness": skewness,
        "residual_excess_kurtosis": excess_kurtosis,
        "absolute_tail_fraction": float(np.mean(np.abs(z) > tail_threshold)),
        "normal_qq_rmse": _normal_qq_rmse(z),
        "group_mean_rms": float(np.sqrt(np.mean(group_means**2))),
        "group_log_second_moment_rms": float(
            np.sqrt(np.mean(group_log_second**2))
        ),
    }


def _simulation_summary(
    observed: dict[str, float],
    simulated: dict[str, np.ndarray],
    *,
    envelope_level: float,
) -> pd.DataFrame:
    alpha = 1.0 - envelope_level
    rows: list[dict[str, Any]] = []
    for metric in _METRIC_ORDER:
        values = np.asarray(simulated[metric], dtype=float)
        lower = float(np.quantile(values, alpha / 2.0))
        upper = float(np.quantile(values, 1.0 - alpha / 2.0))
        observed_value = float(observed[metric])
        below = np.count_nonzero(values < observed_value)
        equal = np.count_nonzero(values == observed_value)
        percentile = float((below + 0.5 * equal) / len(values))
        rows.append(
            {
                "metric": metric,
                "observed": observed_value,
                "simulation_mean": float(np.mean(values)),
                "envelope_lower": lower,
                "envelope_upper": upper,
                "simulation_percentile": percentile,
                "outside_envelope": bool(observed_value < lower or observed_value > upper),
            }
        )
    return pd.DataFrame(rows)


def _canonical_summary(summary: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(summary, pd.DataFrame):
        raise SchemaError("Residual calibration summary must be a pandas DataFrame.")
    if set(summary.columns) != set(_SUMMARY_COLUMNS):
        raise SchemaError("Residual calibration summary columns were altered.")
    canonical = summary.loc[:, _SUMMARY_COLUMNS].reset_index(drop=True)
    if len(canonical) != len(_METRIC_ORDER):
        raise SchemaError("Residual calibration metric inventory is incomplete.")
    if tuple(canonical["metric"].tolist()) != _METRIC_ORDER:
        raise SchemaError("Residual calibration metric inventory or order was altered.")
    numeric_columns = [
        "observed",
        "simulation_mean",
        "envelope_lower",
        "envelope_upper",
        "simulation_percentile",
    ]
    numeric = canonical[numeric_columns].to_numpy(dtype=float)
    if not np.isfinite(numeric).all():
        raise SchemaError("Residual calibration summary contains non-finite values.")
    lower = canonical["envelope_lower"].to_numpy(dtype=float)
    upper = canonical["envelope_upper"].to_numpy(dtype=float)
    if np.any(lower > upper):
        raise SchemaError("Residual calibration envelope bounds are inconsistent.")
    percentiles = canonical["simulation_percentile"].to_numpy(dtype=float)
    if np.any((percentiles < 0.0) | (percentiles > 1.0)):
        raise SchemaError("Residual calibration simulation percentiles are invalid.")
    outside = canonical["outside_envelope"]
    if not all(isinstance(value, (bool, np.bool_)) for value in outside.tolist()):
        raise SchemaError("Residual calibration outside-envelope flags must be boolean.")
    observed = canonical["observed"].to_numpy(dtype=float)
    expected_outside = (observed < lower) | (observed > upper)
    if not np.array_equal(outside.to_numpy(dtype=bool), expected_outside):
        raise SchemaError(
            "Residual calibration outside-envelope flags contradict the bounds."
        )
    return canonical


def _summary_fingerprint(summary: pd.DataFrame) -> str:
    return fingerprint_frame(_canonical_summary(summary))


def _diagnostic_identity_payload(
    *,
    spec: LocationScaleResidualCalibrationSpec,
    model_family: str,
    model_fingerprint: str,
    base_model_certificate_fingerprint: str,
    input_fingerprint: str,
    n_obs: int,
    n_groups: int,
    residuals_fingerprint: str,
    summary_fingerprint: str,
) -> dict[str, Any]:
    return {
        "schema": _DIAGNOSTIC_SCHEMA,
        "spec": spec.to_dict(),
        "model_family": model_family,
        "model_fingerprint_sha256": model_fingerprint,
        "base_model_certificate_fingerprint_sha256": base_model_certificate_fingerprint,
        "input_fingerprint_sha256": input_fingerprint,
        "n_obs": int(n_obs),
        "n_groups": int(n_groups),
        "residuals_fingerprint_sha256": residuals_fingerprint,
        "summary_fingerprint_sha256": summary_fingerprint,
    }


def calibrate_location_scale_residuals(
    result: LocationScaleModelResult,
    data: pd.DataFrame,
    *,
    spec: LocationScaleResidualCalibrationSpec | None = None,
) -> LocationScaleResidualCalibrationResult:
    """Compute simulation-calibrated conditional standardized-residual diagnostics.

    The fitted result must first pass its own model-certificate validator. The
    supplied data must exactly match the modelling input fingerprint stored by
    that result. Reference simulations hold the fitted model fixed and therefore
    do not propagate parameter-estimation uncertainty.
    """
    calibration_spec = spec or LocationScaleResidualCalibrationSpec()
    model_family, model_spec, diagnostic_function = _model_adapter(result)
    base_model_certificate_fingerprint = _require_certifiable_base_model(result)
    input_fingerprint = _require_exact_fitting_input(result, data)
    diagnostics = diagnostic_function(result, data)
    z = diagnostics["standardized_residual"].to_numpy(dtype=float)
    if not np.isfinite(z).all():
        raise SchemaError("Fitted standardized residuals must be finite.")
    group_codes, group_levels = pd.factorize(data[model_spec.group_col], sort=False)
    if np.any(group_codes < 0):
        raise SchemaError("Residual calibration group identities must be complete.")
    n_groups = int(len(group_levels))
    if n_groups < 2:
        raise SchemaError("Residual calibration requires at least two fitted groups.")
    total_draws = len(z) * calibration_spec.n_simulations
    if total_draws > calibration_spec.max_simulated_residual_draws:
        raise SchemaError(
            "Residual calibration simulation budget exceeded: "
            f"{total_draws} requested draws > "
            f"{calibration_spec.max_simulated_residual_draws} allowed."
        )

    observed = _residual_metrics(
        z,
        group_codes,
        n_groups,
        tail_threshold=calibration_spec.absolute_tail_threshold,
    )
    rng = np.random.default_rng(calibration_spec.seed)
    simulated = {
        metric: np.empty(calibration_spec.n_simulations, dtype=float)
        for metric in _METRIC_ORDER
    }
    for simulation_index in range(calibration_spec.n_simulations):
        reference = rng.standard_normal(len(z))
        metrics = _residual_metrics(
            reference,
            group_codes,
            n_groups,
            tail_threshold=calibration_spec.absolute_tail_threshold,
        )
        for metric in _METRIC_ORDER:
            simulated[metric][simulation_index] = metrics[metric]

    summary = _simulation_summary(
        observed,
        simulated,
        envelope_level=calibration_spec.envelope_level,
    )
    residual_frame = pd.DataFrame(
        {
            model_spec.group_col: data[model_spec.group_col].to_numpy(copy=True),
            "location_mean": diagnostics["location_mean"].to_numpy(dtype=float),
            "sigma": diagnostics["sigma"].to_numpy(dtype=float),
            "residual": diagnostics["residual"].to_numpy(dtype=float),
            "standardized_residual": z,
            "group_effect_used": diagnostics["group_effect_used"].to_numpy(dtype=bool),
        },
        index=data.index,
    )
    residuals_fingerprint = fingerprint_frame(residual_frame)
    summary_fingerprint = _summary_fingerprint(summary)
    identity = _diagnostic_identity_payload(
        spec=calibration_spec,
        model_family=model_family,
        model_fingerprint=result.model_fingerprint_sha256,
        base_model_certificate_fingerprint=base_model_certificate_fingerprint,
        input_fingerprint=input_fingerprint,
        n_obs=len(data),
        n_groups=n_groups,
        residuals_fingerprint=residuals_fingerprint,
        summary_fingerprint=summary_fingerprint,
    )
    return LocationScaleResidualCalibrationResult(
        spec=calibration_spec,
        model_family=model_family,
        model_fingerprint_sha256=result.model_fingerprint_sha256,
        base_model_certificate_fingerprint_sha256=base_model_certificate_fingerprint,
        input_fingerprint_sha256=input_fingerprint,
        n_obs=int(len(data)),
        n_groups=n_groups,
        residuals_fingerprint_sha256=residuals_fingerprint,
        summary=summary,
        summary_fingerprint_sha256=summary_fingerprint,
        diagnostic_fingerprint_sha256=benchmark_fingerprint(identity),
    )


def _current_result_identity(result: LocationScaleResidualCalibrationResult) -> dict[str, Any]:
    return _diagnostic_identity_payload(
        spec=result.spec,
        model_family=result.model_family,
        model_fingerprint=result.model_fingerprint_sha256,
        base_model_certificate_fingerprint=result.base_model_certificate_fingerprint_sha256,
        input_fingerprint=result.input_fingerprint_sha256,
        n_obs=result.n_obs,
        n_groups=result.n_groups,
        residuals_fingerprint=result.residuals_fingerprint_sha256,
        summary_fingerprint=_summary_fingerprint(result.summary),
    )


def _validate_result_identity(result: LocationScaleResidualCalibrationResult) -> dict[str, Any]:
    if not isinstance(result, LocationScaleResidualCalibrationResult):
        raise TypeError("result must be a LocationScaleResidualCalibrationResult.")
    if result.model_family not in _SUPPORTED_MODEL_FAMILIES:
        raise SchemaError("Residual calibration model family is invalid.")
    for name, value in (
        ("model_fingerprint_sha256", result.model_fingerprint_sha256),
        (
            "base_model_certificate_fingerprint_sha256",
            result.base_model_certificate_fingerprint_sha256,
        ),
        ("input_fingerprint_sha256", result.input_fingerprint_sha256),
        ("residuals_fingerprint_sha256", result.residuals_fingerprint_sha256),
        ("summary_fingerprint_sha256", result.summary_fingerprint_sha256),
        ("diagnostic_fingerprint_sha256", result.diagnostic_fingerprint_sha256),
    ):
        if not _is_sha256_hex(value):
            raise SchemaError(f"{name} is not a valid SHA-256 fingerprint.")
    expected_summary = _summary_fingerprint(result.summary)
    if expected_summary != result.summary_fingerprint_sha256:
        raise SchemaError("Residual calibration summary was mutated after computation.")
    identity = _current_result_identity(result)
    if benchmark_fingerprint(identity) != result.diagnostic_fingerprint_sha256:
        raise SchemaError("Residual calibration diagnostic fingerprint mismatch.")
    if result.n_obs < 2 or result.n_groups < 2 or result.n_obs < result.n_groups:
        raise SchemaError("Residual calibration observation/group counts are inconsistent.")
    return identity


def build_location_scale_residual_calibration_certificate(
    result: LocationScaleResidualCalibrationResult,
) -> dict[str, Any]:
    """Build a deterministic certificate for conditional residual calibration."""
    identity = _validate_result_identity(result)
    body = {
        "schema": _CERTIFICATE_SCHEMA,
        "diagnostic": identity,
        "diagnostic_fingerprint_sha256": result.diagnostic_fingerprint_sha256,
        "summary": result.summary.to_dict(orient="records"),
        "claim_boundary": dict(_CLAIM_BOUNDARY),
    }
    return {**body, "certificate_fingerprint_sha256": benchmark_fingerprint(body)}


def validate_location_scale_residual_calibration_certificate(
    certificate: dict[str, Any],
) -> None:
    """Fail closed on diagnostic, summary, or scientific-claim tampering."""
    if not isinstance(certificate, dict):
        raise TypeError("certificate must be a dictionary.")
    require_exact_mapping_keys(
        certificate,
        _CERTIFICATE_FIELDS,
        context="Residual calibration certificate",
    )
    if certificate.get("schema") != _CERTIFICATE_SCHEMA:
        raise SchemaError("Unsupported residual calibration certificate schema.")
    fingerprint = certificate.get("certificate_fingerprint_sha256")
    body = {
        key: value
        for key, value in certificate.items()
        if key != "certificate_fingerprint_sha256"
    }
    if not _is_sha256_hex(fingerprint) or fingerprint != benchmark_fingerprint(body):
        raise SchemaError("Residual calibration certificate fingerprint mismatch.")
    if certificate.get("claim_boundary") != _CLAIM_BOUNDARY:
        raise SchemaError("Residual calibration scientific claim boundary was altered.")
    diagnostic = require_exact_mapping_keys(
        certificate.get("diagnostic"),
        _DIAGNOSTIC_FIELDS,
        context="Residual calibration diagnostic identity",
    )
    if diagnostic.get("schema") != _DIAGNOSTIC_SCHEMA:
        raise SchemaError("Residual calibration diagnostic identity is invalid.")
    try:
        canonical_spec = LocationScaleResidualCalibrationSpec(**diagnostic["spec"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SchemaError("Residual calibration certificate has an invalid spec.") from exc
    if benchmark_fingerprint(canonical_spec.to_dict()) != benchmark_fingerprint(
        diagnostic["spec"]
    ):
        raise SchemaError("Residual calibration certificate spec is not canonical.")
    if diagnostic.get("model_family") not in _SUPPORTED_MODEL_FAMILIES:
        raise SchemaError("Residual calibration certificate model family is invalid.")
    for name in (
        "model_fingerprint_sha256",
        "base_model_certificate_fingerprint_sha256",
        "input_fingerprint_sha256",
        "residuals_fingerprint_sha256",
        "summary_fingerprint_sha256",
    ):
        if not _is_sha256_hex(diagnostic.get(name)):
            raise SchemaError(f"Residual calibration certificate {name} is invalid.")
    n_obs = diagnostic.get("n_obs")
    n_groups = diagnostic.get("n_groups")
    if (
        not isinstance(n_obs, int)
        or isinstance(n_obs, bool)
        or not isinstance(n_groups, int)
        or isinstance(n_groups, bool)
        or n_obs < 2
        or n_groups < 2
        or n_obs < n_groups
    ):
        raise SchemaError("Residual calibration certificate counts are invalid.")
    if n_obs * canonical_spec.n_simulations > canonical_spec.max_simulated_residual_draws:
        raise SchemaError("Residual calibration certificate exceeds its simulation budget.")
    summary_records = certificate.get("summary")
    if not isinstance(summary_records, list) or len(summary_records) != len(_METRIC_ORDER):
        raise SchemaError("Residual calibration certificate summary is invalid.")
    summary = pd.DataFrame(summary_records)
    if tuple(summary.get("metric", pd.Series(dtype=str)).tolist()) != _METRIC_ORDER:
        raise SchemaError("Residual calibration certificate metric inventory was altered.")
    if _summary_fingerprint(summary) != diagnostic["summary_fingerprint_sha256"]:
        raise SchemaError("Residual calibration certificate summary fingerprint mismatch.")
    diagnostic_fingerprint = certificate.get("diagnostic_fingerprint_sha256")
    if (
        not _is_sha256_hex(diagnostic_fingerprint)
        or diagnostic_fingerprint != benchmark_fingerprint(diagnostic)
    ):
        raise SchemaError("Residual calibration diagnostic fingerprint mismatch.")


def freeze_location_scale_residual_calibration_certificate(
    result: LocationScaleResidualCalibrationResult,
    path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Validate and freeze a residual-calibration certificate."""
    certificate = build_location_scale_residual_calibration_certificate(result)
    validate_location_scale_residual_calibration_certificate(certificate)
    target = Path(path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"Residual calibration certificate already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(certificate, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return target
