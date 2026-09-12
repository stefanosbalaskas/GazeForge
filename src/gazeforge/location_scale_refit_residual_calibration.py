"""Conditional refit residual calibration for certified location-scale models."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ._certificate_schema import require_exact_mapping_keys
from .benchmarks import benchmark_fingerprint
from .correlated_location_random_slope_scale import (
    CorrelatedLocationRandomSlopeScaleResult,
    fit_correlated_location_random_slope_scale,
)
from .correlated_location_scale import (
    CorrelatedLocationScaleResult,
    fit_correlated_location_scale,
)
from .exceptions import SchemaError
from .hierarchical_location_scale import (
    HierarchicalLocationScaleResult,
    fit_hierarchical_location_scale,
)
from .location_random_slope_scale import (
    LocationRandomSlopeScaleResult,
    fit_location_random_slope_scale,
)
from .location_scale_residual_calibration import (
    _METRIC_ORDER,
    _SUMMARY_COLUMNS,
    LocationScaleModelResult,
    _is_sha256_hex,
    _model_adapter,
    _require_certifiable_base_model,
    _require_exact_fitting_input,
    _residual_metrics,
    _simulation_summary,
    _summary_fingerprint,
)
from .provenance import fingerprint_frame

_CERTIFICATE_SCHEMA = (
    "gazeforge.location-scale-refit-residual-calibration-certificate.v1"
)
_DIAGNOSTIC_SCHEMA = "gazeforge.location-scale-refit-residual-calibration.v1"
_SUPPORTED_MODEL_FAMILIES = frozenset(
    {
        "independent_location_scale",
        "correlated_location_scale",
        "location_random_slope_scale",
        "correlated_location_random_slope_scale",
    }
)
_CERTIFICATE_FIELDS = frozenset(
    {
        "schema",
        "diagnostic",
        "diagnostic_fingerprint_sha256",
        "summary",
        "refit_ledger",
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
        "observed_residuals_fingerprint_sha256",
        "refit_ledger_fingerprint_sha256",
        "summary_fingerprint_sha256",
    }
)
_REFIT_LEDGER_FIELDS = frozenset(
    {
        "simulation_index",
        "model_fingerprint_sha256",
        "model_certificate_fingerprint_sha256",
        "standardized_residuals_fingerprint_sha256",
    }
)
_CLAIM_BOUNDARY = {
    "conditional_refit_residual_calibration_computed": True,
    "outcomes_simulated_from_fitted_conditional_mean_scale": True,
    "observed_predictor_and_group_design_preserved": True,
    "same_model_specification_refit_per_simulation": True,
    "exact_fitting_input_required": True,
    "certifiable_base_model_required": True,
    "every_refit_must_converge_and_be_certifiable": True,
    "model_parameters_refit_per_simulation": True,
    "estimation_procedure_variability_in_reference": True,
    "parameter_estimation_uncertainty_quantified": False,
    "population_random_effects_resampled": False,
    "posterior_random_effect_uncertainty_integrated": False,
    "global_model_adequacy_established": False,
    "distributional_correctness_established": False,
    "fixed_effect_p_values_provided": False,
    "causal_effects_established": False,
    "device_validity_established": False,
    "measurement_validity_established": False,
}


@dataclass(frozen=True, slots=True)
class LocationScaleRefitResidualCalibrationSpec:
    """Specification for conditional parametric refit residual calibration.

    Each replicate simulates outcomes from the fitted conditional location and
    scale on the exact observed predictor/group design, then refits the same
    model specification before recomputing standardized-residual diagnostics.

    The procedure therefore propagates the behaviour of the estimation/refit
    procedure into the reference distribution. It does not sample new
    population random effects, integrate posterior random-effect uncertainty,
    or quantify full parameter-estimation uncertainty.
    """

    n_simulations: int = 100
    seed: int = 2718
    envelope_level: float = 0.95
    absolute_tail_threshold: float = 1.96
    max_refit_rows: int = 100_000

    def __post_init__(self) -> None:
        if (
            not isinstance(self.n_simulations, int)
            or isinstance(self.n_simulations, bool)
            or self.n_simulations < 2
            or self.n_simulations > 10_000
        ):
            raise ValueError(
                "n_simulations must be an integer from 2 through 10000."
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
            not isinstance(self.max_refit_rows, int)
            or isinstance(self.max_refit_rows, bool)
            or self.max_refit_rows < 1
        ):
            raise ValueError("max_refit_rows must be a positive integer.")
        object.__setattr__(self, "envelope_level", level)
        object.__setattr__(self, "absolute_tail_threshold", threshold)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the canonical refit-calibration specification."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LocationScaleRefitResidualCalibrationResult:
    """Conditional refit residual-calibration result."""

    spec: LocationScaleRefitResidualCalibrationSpec
    model_family: str
    model_fingerprint_sha256: str
    base_model_certificate_fingerprint_sha256: str
    input_fingerprint_sha256: str
    n_obs: int
    n_groups: int
    observed_residuals_fingerprint_sha256: str
    refit_ledger: tuple[dict[str, Any], ...]
    refit_ledger_fingerprint_sha256: str
    summary: pd.DataFrame
    summary_fingerprint_sha256: str
    diagnostic_fingerprint_sha256: str

    def metrics(self) -> pd.DataFrame:
        """Return a defensive copy of the metric-envelope table."""
        _validate_result_identity(self)
        return self.summary.copy(deep=True)

    def refits(self) -> pd.DataFrame:
        """Return the deterministic refit lineage ledger."""
        _validate_result_identity(self)
        return pd.DataFrame([dict(row) for row in self.refit_ledger])


def _fit_function_for_result(
    result: LocationScaleModelResult,
) -> Callable[..., LocationScaleModelResult]:
    if isinstance(result, HierarchicalLocationScaleResult):
        return fit_hierarchical_location_scale
    if isinstance(result, CorrelatedLocationScaleResult):
        return fit_correlated_location_scale
    if isinstance(result, CorrelatedLocationRandomSlopeScaleResult):
        return fit_correlated_location_random_slope_scale
    if isinstance(result, LocationRandomSlopeScaleResult):
        return fit_location_random_slope_scale
    raise TypeError(
        "result must be a supported certified location-scale result type."
    )


def _residual_frame_fingerprint(
    data: pd.DataFrame,
    diagnostics: pd.DataFrame,
    *,
    group_col: str,
) -> str:
    frame = pd.DataFrame(
        {
            group_col: data[group_col].to_numpy(copy=True),
            "location_mean": diagnostics["location_mean"].to_numpy(dtype=float),
            "sigma": diagnostics["sigma"].to_numpy(dtype=float),
            "residual": diagnostics["residual"].to_numpy(dtype=float),
            "standardized_residual": diagnostics["standardized_residual"].to_numpy(
                dtype=float
            ),
            "group_effect_used": diagnostics["group_effect_used"].to_numpy(dtype=bool),
        },
        index=data.index,
    )
    return fingerprint_frame(frame)


def _canonical_refit_ledger(
    rows: Any,
    *,
    n_simulations: int,
) -> tuple[dict[str, Any], ...]:
    if not isinstance(rows, (list, tuple)) or len(rows) != n_simulations:
        raise SchemaError("Refit calibration ledger length is invalid.")
    canonical: list[dict[str, Any]] = []
    for expected_index, raw in enumerate(rows):
        row = require_exact_mapping_keys(
            raw,
            _REFIT_LEDGER_FIELDS,
            context="Refit calibration ledger row",
        )
        index = row.get("simulation_index")
        if (
            not isinstance(index, int)
            or isinstance(index, bool)
            or index != expected_index
        ):
            raise SchemaError("Refit calibration ledger indices are invalid.")
        for name in (
            "model_fingerprint_sha256",
            "model_certificate_fingerprint_sha256",
            "standardized_residuals_fingerprint_sha256",
        ):
            if not _is_sha256_hex(row.get(name)):
                raise SchemaError(f"Refit calibration ledger {name} is invalid.")
        canonical.append(dict(row))
    return tuple(canonical)


def _refit_ledger_fingerprint(
    rows: Any,
    *,
    n_simulations: int,
) -> str:
    canonical = _canonical_refit_ledger(rows, n_simulations=n_simulations)
    return benchmark_fingerprint(list(canonical))


def _diagnostic_identity_payload(
    *,
    spec: LocationScaleRefitResidualCalibrationSpec,
    model_family: str,
    model_fingerprint: str,
    base_model_certificate_fingerprint: str,
    input_fingerprint: str,
    n_obs: int,
    n_groups: int,
    observed_residuals_fingerprint: str,
    refit_ledger_fingerprint: str,
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
        "observed_residuals_fingerprint_sha256": observed_residuals_fingerprint,
        "refit_ledger_fingerprint_sha256": refit_ledger_fingerprint,
        "summary_fingerprint_sha256": summary_fingerprint,
    }


def calibrate_location_scale_residuals_with_refits(
    result: LocationScaleModelResult,
    data: pd.DataFrame,
    *,
    spec: LocationScaleRefitResidualCalibrationSpec | None = None,
) -> LocationScaleRefitResidualCalibrationResult:
    """Calibrate residual metrics against conditionally simulated, refitted models.

    The exact fitted modelling input is required. Every simulated outcome uses
    the fitted conditional location and sigma for the observed rows. The same
    model specification is then re-estimated from scratch. Any failed or
    non-certifiable refit aborts the diagnostic rather than being discarded.
    """
    calibration_spec = spec or LocationScaleRefitResidualCalibrationSpec()
    model_family, model_spec, diagnostic_function = _model_adapter(result)
    fit_function = _fit_function_for_result(result)
    base_model_certificate_fingerprint = _require_certifiable_base_model(result)
    input_fingerprint = _require_exact_fitting_input(result, data)
    total_refit_rows = len(data) * calibration_spec.n_simulations
    if total_refit_rows > calibration_spec.max_refit_rows:
        raise SchemaError(
            "Refit residual calibration resource budget exceeded: "
            f"{total_refit_rows} requested refit rows > "
            f"{calibration_spec.max_refit_rows} allowed."
        )

    observed_diagnostics = diagnostic_function(result, data)
    observed_z = observed_diagnostics["standardized_residual"].to_numpy(dtype=float)
    fitted_location = observed_diagnostics["location_mean"].to_numpy(dtype=float)
    fitted_sigma = observed_diagnostics["sigma"].to_numpy(dtype=float)
    if (
        not np.isfinite(observed_z).all()
        or not np.isfinite(fitted_location).all()
        or not np.isfinite(fitted_sigma).all()
        or np.any(fitted_sigma <= 0.0)
    ):
        raise SchemaError("Observed fitted residual calibration values must be finite.")

    group_codes, group_levels = pd.factorize(data[model_spec.group_col], sort=False)
    if np.any(group_codes < 0):
        raise SchemaError("Refit residual calibration group identities must be complete.")
    n_groups = int(len(group_levels))
    if n_groups < 2:
        raise SchemaError("Refit residual calibration requires at least two groups.")

    observed = _residual_metrics(
        observed_z,
        group_codes,
        n_groups,
        tail_threshold=calibration_spec.absolute_tail_threshold,
    )
    simulated = {
        metric: np.empty(calibration_spec.n_simulations, dtype=float)
        for metric in _METRIC_ORDER
    }
    ledger: list[dict[str, Any]] = []
    rng = np.random.default_rng(calibration_spec.seed)
    for simulation_index in range(calibration_spec.n_simulations):
        simulated_data = data.copy(deep=True)
        simulated_data[model_spec.outcome_col] = (
            fitted_location
            + fitted_sigma * rng.standard_normal(len(simulated_data))
        )
        try:
            refitted = fit_function(simulated_data, spec=result.spec)
            refit_certificate_fingerprint = _require_certifiable_base_model(refitted)
            refit_diagnostics = diagnostic_function(refitted, simulated_data)
        except Exception as exc:
            raise SchemaError(
                "Refit residual calibration failed closed because simulation "
                f"{simulation_index} did not produce a converged certifiable refit."
            ) from exc
        refit_z = refit_diagnostics["standardized_residual"].to_numpy(dtype=float)
        if not np.isfinite(refit_z).all():
            raise SchemaError(
                "Refit residual calibration produced non-finite standardized residuals."
            )
        metrics = _residual_metrics(
            refit_z,
            group_codes,
            n_groups,
            tail_threshold=calibration_spec.absolute_tail_threshold,
        )
        for metric in _METRIC_ORDER:
            simulated[metric][simulation_index] = metrics[metric]
        ledger.append(
            {
                "simulation_index": simulation_index,
                "model_fingerprint_sha256": refitted.model_fingerprint_sha256,
                "model_certificate_fingerprint_sha256": refit_certificate_fingerprint,
                "standardized_residuals_fingerprint_sha256": _residual_frame_fingerprint(
                    simulated_data,
                    refit_diagnostics,
                    group_col=model_spec.group_col,
                ),
            }
        )

    summary = _simulation_summary(
        observed,
        simulated,
        envelope_level=calibration_spec.envelope_level,
    )
    canonical_ledger = _canonical_refit_ledger(
        ledger,
        n_simulations=calibration_spec.n_simulations,
    )
    observed_residuals_fingerprint = _residual_frame_fingerprint(
        data,
        observed_diagnostics,
        group_col=model_spec.group_col,
    )
    refit_ledger_fingerprint = _refit_ledger_fingerprint(
        canonical_ledger,
        n_simulations=calibration_spec.n_simulations,
    )
    summary_fingerprint = _summary_fingerprint(summary)
    identity = _diagnostic_identity_payload(
        spec=calibration_spec,
        model_family=model_family,
        model_fingerprint=result.model_fingerprint_sha256,
        base_model_certificate_fingerprint=base_model_certificate_fingerprint,
        input_fingerprint=input_fingerprint,
        n_obs=len(data),
        n_groups=n_groups,
        observed_residuals_fingerprint=observed_residuals_fingerprint,
        refit_ledger_fingerprint=refit_ledger_fingerprint,
        summary_fingerprint=summary_fingerprint,
    )
    return LocationScaleRefitResidualCalibrationResult(
        spec=calibration_spec,
        model_family=model_family,
        model_fingerprint_sha256=result.model_fingerprint_sha256,
        base_model_certificate_fingerprint_sha256=base_model_certificate_fingerprint,
        input_fingerprint_sha256=input_fingerprint,
        n_obs=int(len(data)),
        n_groups=n_groups,
        observed_residuals_fingerprint_sha256=observed_residuals_fingerprint,
        refit_ledger=canonical_ledger,
        refit_ledger_fingerprint_sha256=refit_ledger_fingerprint,
        summary=summary,
        summary_fingerprint_sha256=summary_fingerprint,
        diagnostic_fingerprint_sha256=benchmark_fingerprint(identity),
    )


def _current_result_identity(
    result: LocationScaleRefitResidualCalibrationResult,
) -> dict[str, Any]:
    return _diagnostic_identity_payload(
        spec=result.spec,
        model_family=result.model_family,
        model_fingerprint=result.model_fingerprint_sha256,
        base_model_certificate_fingerprint=result.base_model_certificate_fingerprint_sha256,
        input_fingerprint=result.input_fingerprint_sha256,
        n_obs=result.n_obs,
        n_groups=result.n_groups,
        observed_residuals_fingerprint=result.observed_residuals_fingerprint_sha256,
        refit_ledger_fingerprint=_refit_ledger_fingerprint(
            result.refit_ledger,
            n_simulations=result.spec.n_simulations,
        ),
        summary_fingerprint=_summary_fingerprint(result.summary),
    )


def _validate_result_identity(
    result: LocationScaleRefitResidualCalibrationResult,
) -> dict[str, Any]:
    if not isinstance(result, LocationScaleRefitResidualCalibrationResult):
        raise TypeError("result must be a LocationScaleRefitResidualCalibrationResult.")
    if result.model_family not in _SUPPORTED_MODEL_FAMILIES:
        raise SchemaError("Refit residual calibration model family is invalid.")
    for name, value in (
        ("model_fingerprint_sha256", result.model_fingerprint_sha256),
        (
            "base_model_certificate_fingerprint_sha256",
            result.base_model_certificate_fingerprint_sha256,
        ),
        ("input_fingerprint_sha256", result.input_fingerprint_sha256),
        (
            "observed_residuals_fingerprint_sha256",
            result.observed_residuals_fingerprint_sha256,
        ),
        ("refit_ledger_fingerprint_sha256", result.refit_ledger_fingerprint_sha256),
        ("summary_fingerprint_sha256", result.summary_fingerprint_sha256),
        ("diagnostic_fingerprint_sha256", result.diagnostic_fingerprint_sha256),
    ):
        if not _is_sha256_hex(value):
            raise SchemaError(f"{name} is not a valid SHA-256 fingerprint.")
    if result.n_obs < 2 or result.n_groups < 2 or result.n_obs < result.n_groups:
        raise SchemaError("Refit residual calibration observation/group counts are invalid.")
    if result.n_obs * result.spec.n_simulations > result.spec.max_refit_rows:
        raise SchemaError("Refit residual calibration result exceeds its resource budget.")
    expected_ledger = _refit_ledger_fingerprint(
        result.refit_ledger,
        n_simulations=result.spec.n_simulations,
    )
    if expected_ledger != result.refit_ledger_fingerprint_sha256:
        raise SchemaError("Refit residual calibration ledger was mutated after computation.")
    expected_summary = _summary_fingerprint(result.summary)
    if expected_summary != result.summary_fingerprint_sha256:
        raise SchemaError("Refit residual calibration summary was mutated after computation.")
    identity = _current_result_identity(result)
    if benchmark_fingerprint(identity) != result.diagnostic_fingerprint_sha256:
        raise SchemaError("Refit residual calibration diagnostic fingerprint mismatch.")
    return identity


def build_location_scale_refit_residual_calibration_certificate(
    result: LocationScaleRefitResidualCalibrationResult,
) -> dict[str, Any]:
    """Build a deterministic certificate for conditional refit calibration."""
    identity = _validate_result_identity(result)
    body = {
        "schema": _CERTIFICATE_SCHEMA,
        "diagnostic": identity,
        "diagnostic_fingerprint_sha256": result.diagnostic_fingerprint_sha256,
        "summary": result.summary.to_dict(orient="records"),
        "refit_ledger": [dict(row) for row in result.refit_ledger],
        "claim_boundary": dict(_CLAIM_BOUNDARY),
    }
    return {**body, "certificate_fingerprint_sha256": benchmark_fingerprint(body)}


def validate_location_scale_refit_residual_calibration_certificate(
    certificate: dict[str, Any],
) -> None:
    """Fail closed on refit lineage, summary, schema, or claim tampering."""
    if not isinstance(certificate, dict):
        raise TypeError("certificate must be a dictionary.")
    require_exact_mapping_keys(
        certificate,
        _CERTIFICATE_FIELDS,
        context="Refit residual calibration certificate",
    )
    if certificate.get("schema") != _CERTIFICATE_SCHEMA:
        raise SchemaError("Unsupported refit residual calibration certificate schema.")
    fingerprint = certificate.get("certificate_fingerprint_sha256")
    body = {
        key: value
        for key, value in certificate.items()
        if key != "certificate_fingerprint_sha256"
    }
    if not _is_sha256_hex(fingerprint) or fingerprint != benchmark_fingerprint(body):
        raise SchemaError("Refit residual calibration certificate fingerprint mismatch.")
    if certificate.get("claim_boundary") != _CLAIM_BOUNDARY:
        raise SchemaError("Refit residual calibration scientific claim boundary was altered.")
    diagnostic = require_exact_mapping_keys(
        certificate.get("diagnostic"),
        _DIAGNOSTIC_FIELDS,
        context="Refit residual calibration diagnostic identity",
    )
    if diagnostic.get("schema") != _DIAGNOSTIC_SCHEMA:
        raise SchemaError("Refit residual calibration diagnostic identity is invalid.")
    try:
        canonical_spec = LocationScaleRefitResidualCalibrationSpec(**diagnostic["spec"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SchemaError("Refit residual calibration certificate has an invalid spec.") from exc
    if benchmark_fingerprint(canonical_spec.to_dict()) != benchmark_fingerprint(
        diagnostic["spec"]
    ):
        raise SchemaError("Refit residual calibration certificate spec is not canonical.")
    if diagnostic.get("model_family") not in _SUPPORTED_MODEL_FAMILIES:
        raise SchemaError("Refit residual calibration certificate model family is invalid.")
    for name in (
        "model_fingerprint_sha256",
        "base_model_certificate_fingerprint_sha256",
        "input_fingerprint_sha256",
        "observed_residuals_fingerprint_sha256",
        "refit_ledger_fingerprint_sha256",
        "summary_fingerprint_sha256",
    ):
        if not _is_sha256_hex(diagnostic.get(name)):
            raise SchemaError(f"Refit residual calibration certificate {name} is invalid.")
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
        raise SchemaError("Refit residual calibration certificate counts are invalid.")
    if n_obs * canonical_spec.n_simulations > canonical_spec.max_refit_rows:
        raise SchemaError("Refit residual calibration certificate exceeds its resource budget.")
    ledger = _canonical_refit_ledger(
        certificate.get("refit_ledger"),
        n_simulations=canonical_spec.n_simulations,
    )
    if (
        benchmark_fingerprint(list(ledger))
        != diagnostic["refit_ledger_fingerprint_sha256"]
    ):
        raise SchemaError("Refit residual calibration ledger fingerprint mismatch.")
    summary_records = certificate.get("summary")
    if not isinstance(summary_records, list) or len(summary_records) != len(_METRIC_ORDER):
        raise SchemaError("Refit residual calibration certificate summary is invalid.")
    summary = pd.DataFrame(summary_records)
    if tuple(summary.get("metric", pd.Series(dtype=str)).tolist()) != _METRIC_ORDER:
        raise SchemaError("Refit residual calibration certificate metric inventory was altered.")
    if set(summary.columns) != set(_SUMMARY_COLUMNS):
        raise SchemaError("Refit residual calibration summary columns were altered.")
    if _summary_fingerprint(summary) != diagnostic["summary_fingerprint_sha256"]:
        raise SchemaError("Refit residual calibration certificate summary fingerprint mismatch.")
    diagnostic_fingerprint = certificate.get("diagnostic_fingerprint_sha256")
    if (
        not _is_sha256_hex(diagnostic_fingerprint)
        or diagnostic_fingerprint != benchmark_fingerprint(diagnostic)
    ):
        raise SchemaError("Refit residual calibration diagnostic fingerprint mismatch.")


def freeze_location_scale_refit_residual_calibration_certificate(
    result: LocationScaleRefitResidualCalibrationResult,
    path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Validate and freeze a refit-calibration certificate as canonical JSON."""
    certificate = build_location_scale_refit_residual_calibration_certificate(result)
    validate_location_scale_refit_residual_calibration_certificate(certificate)
    destination = Path(path)
    if destination.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(certificate, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return destination
