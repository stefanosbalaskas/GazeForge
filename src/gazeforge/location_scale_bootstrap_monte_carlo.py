"""Monte Carlo precision diagnostics for hierarchical bootstrap summaries."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import binom

from ._certificate_schema import require_exact_mapping_keys
from .benchmarks import benchmark_fingerprint
from .exceptions import SchemaError
from .location_scale_hierarchical_bootstrap import (
    LocationScaleHierarchicalBootstrapResult,
    build_location_scale_hierarchical_bootstrap_certificate,
    validate_location_scale_hierarchical_bootstrap_certificate,
)

_CERTIFICATE_SCHEMA = (
    "gazeforge.location-scale-bootstrap-monte-carlo-certificate.v1"
)
_ASSESSMENT_SCHEMA = "gazeforge.location-scale-bootstrap-monte-carlo.v1"

_DIAGNOSTIC_FIELDS = frozenset(
    {
        "parameter_id",
        "component",
        "term",
        "n_simulations",
        "bootstrap_mean",
        "bootstrap_se",
        "mean_mcse",
        "bootstrap_se_mcse_jackknife",
        "interval_lower",
        "interval_lower_probability",
        "interval_lower_mc_rank_lower",
        "interval_lower_mc_rank_upper",
        "interval_lower_mc_band_lower",
        "interval_lower_mc_band_upper",
        "interval_lower_mc_binomial_coverage",
        "interval_upper",
        "interval_upper_probability",
        "interval_upper_mc_rank_lower",
        "interval_upper_mc_rank_upper",
        "interval_upper_mc_band_lower",
        "interval_upper_mc_band_upper",
        "interval_upper_mc_binomial_coverage",
    }
)

_ASSESSMENT_FIELDS = frozenset(
    {
        "schema",
        "spec",
        "source_bootstrap_fingerprint_sha256",
        "source_bootstrap_certificate_fingerprint_sha256",
        "model_family",
        "bootstrap_interval_level",
        "n_simulations",
        "parameter_ids",
        "diagnostics_fingerprint_sha256",
    }
)

_CERTIFICATE_FIELDS = frozenset(
    {
        "schema",
        "assessment",
        "assessment_fingerprint_sha256",
        "source_bootstrap_certificate",
        "diagnostics",
        "claim_boundary",
        "certificate_fingerprint_sha256",
    }
)

_CLAIM_BOUNDARY = {
    "bootstrap_monte_carlo_precision_quantified": True,
    "mean_mcse_computed": True,
    "bootstrap_se_jackknife_mcse_computed": True,
    "percentile_endpoint_binomial_order_statistic_bands_computed": True,
    "existing_bootstrap_replicates_only": True,
    "additional_model_refits_performed": False,
    "automatic_stability_threshold_applied": False,
    "minimum_simulation_count_declared_adequate": False,
    "bootstrap_interval_coverage_guaranteed": False,
    "model_misspecification_robust": False,
    "global_model_adequacy_established": False,
    "distributional_correctness_established": False,
    "fixed_effect_p_values_provided": False,
    "causal_effects_established": False,
    "device_validity_established": False,
    "measurement_validity_established": False,
}


@dataclass(frozen=True, slots=True)
class LocationScaleBootstrapMonteCarloSpec:
    """Specification for bootstrap Monte Carlo precision diagnostics."""

    confidence_level: float = 0.95

    def __post_init__(self) -> None:
        level = float(self.confidence_level)
        if not np.isfinite(level) or not 0.5 < level < 1.0:
            raise ValueError(
                "confidence_level must be finite and between 0.5 and 1.0."
            )
        object.__setattr__(self, "confidence_level", level)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the canonical Monte Carlo diagnostic specification."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LocationScaleBootstrapMonteCarloResult:
    """Monte Carlo precision diagnostics for one certified bootstrap result."""

    spec: LocationScaleBootstrapMonteCarloSpec
    source_bootstrap_fingerprint_sha256: str
    source_bootstrap_certificate_fingerprint_sha256: str
    source_bootstrap_certificate_json: str
    model_family: str
    bootstrap_interval_level: float
    n_simulations: int
    parameter_ids: tuple[str, ...]
    diagnostics: tuple[dict[str, Any], ...]
    diagnostics_fingerprint_sha256: str
    assessment_fingerprint_sha256: str

    def parameters(self) -> pd.DataFrame:
        """Return a defensive tabular copy of the Monte Carlo diagnostics."""
        _validate_result_identity(self)
        return pd.DataFrame([dict(row) for row in self.diagnostics])


def _is_sha256_hex(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _jackknife_sd_mcse(values: np.ndarray) -> float:
    n = int(len(values))
    if n < 3:
        raise SchemaError(
            "Monte Carlo precision diagnostics require at least three "
            "bootstrap simulations."
        )
    total = float(np.sum(values))
    total_sq = float(np.dot(values, values))
    leave_one_out = np.empty(n, dtype=float)
    remaining_n = n - 1
    for index, value in enumerate(values):
        remaining_sum = total - float(value)
        remaining_sq = total_sq - float(value) ** 2
        centered_ss = remaining_sq - remaining_sum**2 / remaining_n
        variance = centered_ss / (remaining_n - 1)
        if variance < 0.0 and abs(variance) <= 1e-12:
            variance = 0.0
        if variance < 0.0 or not np.isfinite(variance):
            raise SchemaError(
                "Bootstrap SD jackknife produced an invalid leave-one-out "
                "variance."
            )
        leave_one_out[index] = np.sqrt(variance)
    center = float(np.mean(leave_one_out))
    value = np.sqrt(
        (n - 1.0) / n
        * float(np.sum((leave_one_out - center) ** 2))
    )
    if not np.isfinite(value):
        raise SchemaError("Bootstrap SD jackknife MCSE is non-finite.")
    return float(value)


def _order_statistic_quantile_band(
    values: np.ndarray,
    *,
    probability: float,
    confidence_level: float,
) -> dict[str, Any]:
    n = int(len(values))
    if n < 1 or not np.isfinite(values).all():
        raise SchemaError("Bootstrap replicate estimates are invalid.")
    if not 0.0 < probability < 1.0:
        raise ValueError("probability must be strictly between 0 and 1.")

    alpha = 1.0 - confidence_level
    lower_count = int(binom.ppf(alpha / 2.0, n, probability))
    upper_count = int(binom.ppf(1.0 - alpha / 2.0, n, probability))
    lower_count = max(0, min(lower_count, n))
    upper_count = max(lower_count, min(upper_count, n))

    ordered = np.sort(values)
    lower_rank = lower_count
    upper_rank = upper_count + 1

    lower_value: float | None
    upper_value: float | None
    if lower_rank == 0:
        lower_value = None
    else:
        lower_value = float(ordered[lower_rank - 1])
    if upper_rank == n + 1:
        upper_value = None
    else:
        upper_value = float(ordered[upper_rank - 1])

    lower_tail = float(binom.cdf(lower_count - 1, n, probability))
    upper_tail = float(binom.sf(upper_count, n, probability))
    coverage = 1.0 - lower_tail - upper_tail
    if not np.isfinite(coverage) or coverage < confidence_level - 1e-12:
        raise SchemaError(
            "Binomial order-statistic Monte Carlo band failed its requested "
            "coverage check."
        )

    return {
        "rank_lower": lower_rank,
        "rank_upper": upper_rank,
        "band_lower": lower_value,
        "band_upper": upper_value,
        "binomial_coverage": float(coverage),
    }


def _canonical_optional_float(value: Any, *, context: str) -> float | None:
    if value is None:
        return None
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not np.isfinite(float(value))
    ):
        raise SchemaError(f"{context} must be finite or null.")
    return float(value)


def _canonical_diagnostics(
    rows: Any,
    *,
    n_simulations: int,
    parameter_ids: tuple[str, ...],
) -> tuple[dict[str, Any], ...]:
    if not isinstance(rows, (list, tuple)) or len(rows) != len(parameter_ids):
        raise SchemaError("Bootstrap Monte Carlo diagnostics are invalid.")
    canonical: list[dict[str, Any]] = []
    for expected_parameter_id, raw in zip(parameter_ids, rows, strict=True):
        row = require_exact_mapping_keys(
            raw,
            _DIAGNOSTIC_FIELDS,
            context="Bootstrap Monte Carlo diagnostic row",
        )
        parameter_id = row.get("parameter_id")
        component = row.get("component")
        term = row.get("term")
        if (
            parameter_id != expected_parameter_id
            or not isinstance(component, str)
            or not component
            or not isinstance(term, str)
            or not term
        ):
            raise SchemaError("Bootstrap Monte Carlo diagnostic identity is invalid.")
        if row.get("n_simulations") != n_simulations:
            raise SchemaError(
                "Bootstrap Monte Carlo diagnostic simulation count mismatch."
            )

        numeric_names = (
            "bootstrap_mean",
            "bootstrap_se",
            "mean_mcse",
            "bootstrap_se_mcse_jackknife",
            "interval_lower",
            "interval_lower_probability",
            "interval_lower_mc_binomial_coverage",
            "interval_upper",
            "interval_upper_probability",
            "interval_upper_mc_binomial_coverage",
        )
        numeric: dict[str, float] = {}
        for name in numeric_names:
            value = row.get(name)
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not np.isfinite(float(value))
            ):
                raise SchemaError(
                    f"Bootstrap Monte Carlo diagnostic {name} is invalid."
                )
            numeric[name] = float(value)

        for name in (
            "interval_lower_mc_rank_lower",
            "interval_lower_mc_rank_upper",
            "interval_upper_mc_rank_lower",
            "interval_upper_mc_rank_upper",
        ):
            value = row.get(name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
                or value > n_simulations + 1
            ):
                raise SchemaError(
                    f"Bootstrap Monte Carlo diagnostic {name} is invalid."
                )

        canonical.append(
            {
                "parameter_id": parameter_id,
                "component": component,
                "term": term,
                "n_simulations": n_simulations,
                **numeric,
                "interval_lower_mc_rank_lower": row[
                    "interval_lower_mc_rank_lower"
                ],
                "interval_lower_mc_rank_upper": row[
                    "interval_lower_mc_rank_upper"
                ],
                "interval_lower_mc_band_lower": _canonical_optional_float(
                    row.get("interval_lower_mc_band_lower"),
                    context="Lower percentile Monte Carlo band lower endpoint",
                ),
                "interval_lower_mc_band_upper": _canonical_optional_float(
                    row.get("interval_lower_mc_band_upper"),
                    context="Lower percentile Monte Carlo band upper endpoint",
                ),
                "interval_upper_mc_rank_lower": row[
                    "interval_upper_mc_rank_lower"
                ],
                "interval_upper_mc_rank_upper": row[
                    "interval_upper_mc_rank_upper"
                ],
                "interval_upper_mc_band_lower": _canonical_optional_float(
                    row.get("interval_upper_mc_band_lower"),
                    context="Upper percentile Monte Carlo band lower endpoint",
                ),
                "interval_upper_mc_band_upper": _canonical_optional_float(
                    row.get("interval_upper_mc_band_upper"),
                    context="Upper percentile Monte Carlo band upper endpoint",
                ),
            }
        )
    return tuple(canonical)


def _diagnostics_from_bootstrap_certificate(
    bootstrap_certificate: dict[str, Any],
    *,
    spec: LocationScaleBootstrapMonteCarloSpec,
) -> tuple[dict[str, Any], ...]:
    validate_location_scale_hierarchical_bootstrap_certificate(
        bootstrap_certificate
    )
    bootstrap = bootstrap_certificate["bootstrap"]
    bootstrap_spec = bootstrap["spec"]
    n_simulations = int(bootstrap_spec["n_simulations"])
    if n_simulations < 3:
        raise SchemaError(
            "Monte Carlo precision diagnostics require at least three "
            "bootstrap simulations."
        )
    interval_level = float(bootstrap_spec["interval_level"])
    alpha = 1.0 - interval_level
    lower_probability = alpha / 2.0
    upper_probability = 1.0 - alpha / 2.0

    inventory = bootstrap["parameter_inventory"]
    summary_by_id = {
        row["parameter_id"]: row for row in bootstrap_certificate["summary"]
    }
    ledger = bootstrap_certificate["refit_ledger"]

    diagnostics: list[dict[str, Any]] = []
    for parameter in inventory:
        parameter_id = parameter["parameter_id"]
        values = np.asarray(
            [
                row["parameter_estimates"][parameter_id]
                for row in ledger
            ],
            dtype=float,
        )
        if (
            len(values) != n_simulations
            or not np.isfinite(values).all()
        ):
            raise SchemaError("Bootstrap replicate estimates are invalid.")
        summary = summary_by_id[parameter_id]
        bootstrap_se = float(summary["bootstrap_se"])
        if bootstrap_se < 0.0 or not np.isfinite(bootstrap_se):
            raise SchemaError("Bootstrap standard error is invalid.")

        lower_band = _order_statistic_quantile_band(
            values,
            probability=lower_probability,
            confidence_level=spec.confidence_level,
        )
        upper_band = _order_statistic_quantile_band(
            values,
            probability=upper_probability,
            confidence_level=spec.confidence_level,
        )
        diagnostics.append(
            {
                "parameter_id": parameter_id,
                "component": parameter["component"],
                "term": parameter["term"],
                "n_simulations": n_simulations,
                "bootstrap_mean": float(summary["bootstrap_mean"]),
                "bootstrap_se": bootstrap_se,
                "mean_mcse": float(bootstrap_se / np.sqrt(n_simulations)),
                "bootstrap_se_mcse_jackknife": _jackknife_sd_mcse(values),
                "interval_lower": float(summary["interval_lower"]),
                "interval_lower_probability": float(lower_probability),
                "interval_lower_mc_rank_lower": lower_band["rank_lower"],
                "interval_lower_mc_rank_upper": lower_band["rank_upper"],
                "interval_lower_mc_band_lower": lower_band["band_lower"],
                "interval_lower_mc_band_upper": lower_band["band_upper"],
                "interval_lower_mc_binomial_coverage": lower_band[
                    "binomial_coverage"
                ],
                "interval_upper": float(summary["interval_upper"]),
                "interval_upper_probability": float(upper_probability),
                "interval_upper_mc_rank_lower": upper_band["rank_lower"],
                "interval_upper_mc_rank_upper": upper_band["rank_upper"],
                "interval_upper_mc_band_lower": upper_band["band_lower"],
                "interval_upper_mc_band_upper": upper_band["band_upper"],
                "interval_upper_mc_binomial_coverage": upper_band[
                    "binomial_coverage"
                ],
            }
        )
    parameter_ids = tuple(row["parameter_id"] for row in inventory)
    return _canonical_diagnostics(
        diagnostics,
        n_simulations=n_simulations,
        parameter_ids=parameter_ids,
    )


def _assessment_identity(
    *,
    spec: LocationScaleBootstrapMonteCarloSpec,
    bootstrap_certificate: dict[str, Any],
    diagnostics_fingerprint: str,
) -> dict[str, Any]:
    bootstrap = bootstrap_certificate["bootstrap"]
    parameter_ids = [
        row["parameter_id"] for row in bootstrap["parameter_inventory"]
    ]
    return {
        "schema": _ASSESSMENT_SCHEMA,
        "spec": spec.to_dict(),
        "source_bootstrap_fingerprint_sha256": bootstrap_certificate[
            "bootstrap_fingerprint_sha256"
        ],
        "source_bootstrap_certificate_fingerprint_sha256": bootstrap_certificate[
            "certificate_fingerprint_sha256"
        ],
        "model_family": bootstrap["model_family"],
        "bootstrap_interval_level": float(
            bootstrap["spec"]["interval_level"]
        ),
        "n_simulations": int(bootstrap["spec"]["n_simulations"]),
        "parameter_ids": parameter_ids,
        "diagnostics_fingerprint_sha256": diagnostics_fingerprint,
    }


def assess_location_scale_bootstrap_monte_carlo(
    result: LocationScaleHierarchicalBootstrapResult,
    *,
    spec: LocationScaleBootstrapMonteCarloSpec | None = None,
) -> LocationScaleBootstrapMonteCarloResult:
    """Quantify Monte Carlo error in one certified hierarchical bootstrap."""
    if not isinstance(result, LocationScaleHierarchicalBootstrapResult):
        raise TypeError(
            "result must be a LocationScaleHierarchicalBootstrapResult."
        )
    diagnostic_spec = spec or LocationScaleBootstrapMonteCarloSpec()
    bootstrap_certificate = (
        build_location_scale_hierarchical_bootstrap_certificate(result)
    )
    validate_location_scale_hierarchical_bootstrap_certificate(
        bootstrap_certificate
    )
    diagnostics = _diagnostics_from_bootstrap_certificate(
        bootstrap_certificate,
        spec=diagnostic_spec,
    )
    diagnostics_fingerprint = benchmark_fingerprint(list(diagnostics))
    identity = _assessment_identity(
        spec=diagnostic_spec,
        bootstrap_certificate=bootstrap_certificate,
        diagnostics_fingerprint=diagnostics_fingerprint,
    )
    source_json = json.dumps(
        bootstrap_certificate,
        sort_keys=True,
        separators=(",", ":"),
    )
    return LocationScaleBootstrapMonteCarloResult(
        spec=diagnostic_spec,
        source_bootstrap_fingerprint_sha256=bootstrap_certificate[
            "bootstrap_fingerprint_sha256"
        ],
        source_bootstrap_certificate_fingerprint_sha256=bootstrap_certificate[
            "certificate_fingerprint_sha256"
        ],
        source_bootstrap_certificate_json=source_json,
        model_family=bootstrap_certificate["bootstrap"]["model_family"],
        bootstrap_interval_level=float(
            bootstrap_certificate["bootstrap"]["spec"]["interval_level"]
        ),
        n_simulations=int(
            bootstrap_certificate["bootstrap"]["spec"]["n_simulations"]
        ),
        parameter_ids=tuple(identity["parameter_ids"]),
        diagnostics=diagnostics,
        diagnostics_fingerprint_sha256=diagnostics_fingerprint,
        assessment_fingerprint_sha256=benchmark_fingerprint(identity),
    )


def _source_certificate_from_result(
    result: LocationScaleBootstrapMonteCarloResult,
) -> dict[str, Any]:
    try:
        source = json.loads(result.source_bootstrap_certificate_json)
    except (TypeError, json.JSONDecodeError) as exc:
        raise SchemaError(
            "Stored source bootstrap certificate JSON is invalid."
        ) from exc
    validate_location_scale_hierarchical_bootstrap_certificate(source)
    if (
        source["bootstrap_fingerprint_sha256"]
        != result.source_bootstrap_fingerprint_sha256
        or source["certificate_fingerprint_sha256"]
        != result.source_bootstrap_certificate_fingerprint_sha256
    ):
        raise SchemaError(
            "Monte Carlo result source-bootstrap lineage mismatch."
        )
    return source


def _validate_result_identity(
    result: LocationScaleBootstrapMonteCarloResult,
) -> dict[str, Any]:
    if not isinstance(result, LocationScaleBootstrapMonteCarloResult):
        raise TypeError(
            "result must be a LocationScaleBootstrapMonteCarloResult."
        )
    source = _source_certificate_from_result(result)
    expected_diagnostics = _diagnostics_from_bootstrap_certificate(
        source,
        spec=result.spec,
    )
    if expected_diagnostics != result.diagnostics:
        raise SchemaError(
            "Bootstrap Monte Carlo diagnostics were mutated after computation."
        )
    diagnostics_fingerprint = benchmark_fingerprint(
        list(expected_diagnostics)
    )
    if diagnostics_fingerprint != result.diagnostics_fingerprint_sha256:
        raise SchemaError(
            "Bootstrap Monte Carlo diagnostics fingerprint mismatch."
        )
    identity = _assessment_identity(
        spec=result.spec,
        bootstrap_certificate=source,
        diagnostics_fingerprint=diagnostics_fingerprint,
    )
    if (
        result.model_family != identity["model_family"]
        or result.bootstrap_interval_level
        != identity["bootstrap_interval_level"]
        or result.n_simulations != identity["n_simulations"]
        or list(result.parameter_ids) != identity["parameter_ids"]
    ):
        raise SchemaError("Bootstrap Monte Carlo result identity mismatch.")
    if not _is_sha256_hex(result.assessment_fingerprint_sha256):
        raise SchemaError(
            "Bootstrap Monte Carlo assessment fingerprint is invalid."
        )
    if (
        benchmark_fingerprint(identity)
        != result.assessment_fingerprint_sha256
    ):
        raise SchemaError(
            "Bootstrap Monte Carlo assessment fingerprint mismatch."
        )
    return identity


def build_location_scale_bootstrap_monte_carlo_certificate(
    result: LocationScaleBootstrapMonteCarloResult,
) -> dict[str, Any]:
    """Build a deterministic certificate for bootstrap Monte Carlo precision."""
    identity = _validate_result_identity(result)
    source = _source_certificate_from_result(result)
    body = {
        "schema": _CERTIFICATE_SCHEMA,
        "assessment": identity,
        "assessment_fingerprint_sha256": result.assessment_fingerprint_sha256,
        "source_bootstrap_certificate": source,
        "diagnostics": [dict(row) for row in result.diagnostics],
        "claim_boundary": dict(_CLAIM_BOUNDARY),
    }
    return {
        **body,
        "certificate_fingerprint_sha256": benchmark_fingerprint(body),
    }


def validate_location_scale_bootstrap_monte_carlo_certificate(
    certificate: dict[str, Any],
) -> None:
    """Fail closed on Monte Carlo diagnostic, lineage, or claim tampering."""
    if not isinstance(certificate, dict):
        raise TypeError("certificate must be a dictionary.")
    require_exact_mapping_keys(
        certificate,
        _CERTIFICATE_FIELDS,
        context="Bootstrap Monte Carlo certificate",
    )
    if certificate.get("schema") != _CERTIFICATE_SCHEMA:
        raise SchemaError(
            "Unsupported bootstrap Monte Carlo certificate schema."
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
            "Bootstrap Monte Carlo certificate fingerprint mismatch."
        )
    if certificate.get("claim_boundary") != _CLAIM_BOUNDARY:
        raise SchemaError(
            "Bootstrap Monte Carlo scientific claim boundary was altered."
        )

    source = certificate.get("source_bootstrap_certificate")
    validate_location_scale_hierarchical_bootstrap_certificate(source)
    assessment = require_exact_mapping_keys(
        certificate.get("assessment"),
        _ASSESSMENT_FIELDS,
        context="Bootstrap Monte Carlo assessment identity",
    )
    if assessment.get("schema") != _ASSESSMENT_SCHEMA:
        raise SchemaError(
            "Bootstrap Monte Carlo assessment identity is invalid."
        )
    try:
        spec = LocationScaleBootstrapMonteCarloSpec(
            **assessment["spec"]
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SchemaError(
            "Bootstrap Monte Carlo certificate has an invalid spec."
        ) from exc
    if benchmark_fingerprint(spec.to_dict()) != benchmark_fingerprint(
        assessment["spec"]
    ):
        raise SchemaError(
            "Bootstrap Monte Carlo certificate spec is not canonical."
        )

    source_bootstrap = source["bootstrap"]
    parameter_ids = tuple(
        row["parameter_id"]
        for row in source_bootstrap["parameter_inventory"]
    )
    n_simulations = int(source_bootstrap["spec"]["n_simulations"])
    expected_diagnostics = _diagnostics_from_bootstrap_certificate(
        source,
        spec=spec,
    )
    diagnostics = _canonical_diagnostics(
        certificate.get("diagnostics"),
        n_simulations=n_simulations,
        parameter_ids=parameter_ids,
    )
    if diagnostics != expected_diagnostics:
        raise SchemaError(
            "Bootstrap Monte Carlo diagnostics are inconsistent with the "
            "source bootstrap certificate."
        )
    diagnostics_fingerprint = benchmark_fingerprint(list(diagnostics))
    expected_identity = _assessment_identity(
        spec=spec,
        bootstrap_certificate=source,
        diagnostics_fingerprint=diagnostics_fingerprint,
    )
    if assessment != expected_identity:
        raise SchemaError(
            "Bootstrap Monte Carlo assessment identity mismatch."
        )
    assessment_fingerprint = certificate.get(
        "assessment_fingerprint_sha256"
    )
    if (
        not _is_sha256_hex(assessment_fingerprint)
        or assessment_fingerprint
        != benchmark_fingerprint(expected_identity)
    ):
        raise SchemaError(
            "Bootstrap Monte Carlo assessment fingerprint mismatch."
        )


def freeze_location_scale_bootstrap_monte_carlo_certificate(
    result: LocationScaleBootstrapMonteCarloResult,
    path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Validate and freeze Monte Carlo diagnostics as canonical JSON."""
    certificate = build_location_scale_bootstrap_monte_carlo_certificate(
        result
    )
    validate_location_scale_bootstrap_monte_carlo_certificate(certificate)
    destination = Path(path)
    if destination.exists() and not overwrite:
        raise FileExistsError(
            f"Refusing to overwrite existing file: {destination}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(certificate, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return destination


__all__ = [
    "LocationScaleBootstrapMonteCarloResult",
    "LocationScaleBootstrapMonteCarloSpec",
    "assess_location_scale_bootstrap_monte_carlo",
    "build_location_scale_bootstrap_monte_carlo_certificate",
    "freeze_location_scale_bootstrap_monte_carlo_certificate",
    "validate_location_scale_bootstrap_monte_carlo_certificate",
]
