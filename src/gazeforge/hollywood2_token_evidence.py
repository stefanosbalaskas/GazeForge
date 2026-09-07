"""Deterministic publication layer for Hollywood2 source-token validation reports.

The underlying model comparison uses ordinary floating-point arithmetic. Independent reruns can
therefore differ in the last machine-representable bits of aggregate metrics even when the held-out
rows, folds, source identities, predictions, and scientifically meaningful results are unchanged.
Frozen evidence needs an explicit serialization contract for those finite metric floats.

Version 1 rounded finite values in the ``metrics`` subtree to 15 decimal places and is retained for
historical replay. Version 2 moved to 14 places after last-bit hardware/BLAS drift was observed, but
a later full-report cross-worker diagnostic showed one fold-level Brier value straddling a 14-place
rounding boundary. Version 3 therefore rounds the same metrics-only subtree to 13 decimal places,
the highest precision that reproduced the reviewed full report byte-for-byte on the independent
diagnostic worker. Benchmark metadata, model configuration, protocol settings, source identities,
and scientific claim boundaries are never rounded or rewritten by any contract.
"""

from __future__ import annotations

import copy
import math
from typing import Any

import numpy as np

from .benchmarks import benchmark_fingerprint
from .exceptions import BenchmarkIntegrityError
from .hollywood2_token_validation import (
    validate_hollywood2_source_token_validation_report,
)

HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES_V1 = 15
HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES_V2 = 14
HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES_V3 = 13

HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V1 = {
    "method": "recursive_round_finite_metric_floats",
    "metric_float_decimal_places": HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES_V1,
    "nonfinite_metric_floats_permitted": False,
    "benchmark_model_protocol_numeric_values_rounded": False,
}
HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V2 = {
    "method": "recursive_round_finite_metric_floats",
    "metric_float_decimal_places": HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES_V2,
    "nonfinite_metric_floats_permitted": False,
    "benchmark_model_protocol_numeric_values_rounded": False,
}
HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V3 = {
    "method": "recursive_round_finite_metric_floats",
    "metric_float_decimal_places": HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES_V3,
    "nonfinite_metric_floats_permitted": False,
    "benchmark_model_protocol_numeric_values_rounded": False,
}

# Public aliases identify the current publication contract. Historical validation must import the
# explicit versioned names above rather than relying on these aliases.
HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES = (
    HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES_V3
)
HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION = dict(
    HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V3
)


def _validate_numeric_canonicalization_contract(
    contract: dict[str, Any],
) -> dict[str, Any]:
    if contract not in (
        HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V1,
        HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V2,
        HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V3,
    ):
        raise BenchmarkIntegrityError(
            "Hollywood2 numeric canonicalization must use a reviewed v1, v2, or v3 contract."
        )
    return dict(contract)


def _canonicalize_metric_value(
    value: Any,
    *,
    decimal_places: int = HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES,
) -> Any:
    if decimal_places not in {
        HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES_V1,
        HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES_V2,
        HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES_V3,
    }:
        raise BenchmarkIntegrityError(
            "Hollywood2 metric canonicalization supports only reviewed 13-, 14-, or 15-place "
            "contracts."
        )
    if isinstance(value, dict):
        return {
            str(key): _canonicalize_metric_value(item, decimal_places=decimal_places)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _canonicalize_metric_value(item, decimal_places=decimal_places)
            for item in value
        ]
    if isinstance(value, tuple):
        return [
            _canonicalize_metric_value(item, decimal_places=decimal_places)
            for item in value
        ]
    if isinstance(value, (float, np.floating)):
        numeric = float(value)
        if not math.isfinite(numeric):
            raise BenchmarkIntegrityError(
                "Hollywood2 frozen metrics must not contain non-finite floating-point values."
            )
        return round(numeric, decimal_places)
    if isinstance(value, np.integer):
        return int(value)
    return value


def canonicalize_hollywood2_source_token_validation_report(
    report: dict[str, Any],
    *,
    numeric_canonicalization: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a fingerprint-stable publication copy of a validated source-token report.

    Only the ``metrics`` subtree is numerically canonicalized. The requested reviewed contract is
    recorded in the protocol, then the report fingerprint is recomputed and the complete
    Hollywood2 scientific claim boundary is revalidated.

    The default is the current v3 portability contract. Pass an explicit versioned contract to
    replay historical v1 or v2 publication evidence.
    """
    validated = validate_hollywood2_source_token_validation_report(report)
    output = copy.deepcopy(validated)
    metrics = output.get("metrics")
    protocol = output.get("protocol")
    if not isinstance(metrics, dict) or not isinstance(protocol, dict):
        raise BenchmarkIntegrityError(
            "Hollywood2 source-token report is missing metrics or protocol metadata."
        )

    contract_input = (
        HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V3
        if numeric_canonicalization is None
        else numeric_canonicalization
    )
    contract = _validate_numeric_canonicalization_contract(contract_input)
    decimal_places = int(contract["metric_float_decimal_places"])
    output["metrics"] = _canonicalize_metric_value(
        metrics,
        decimal_places=decimal_places,
    )
    protocol["numeric_canonicalization"] = contract

    body = dict(output)
    body.pop("report_fingerprint_sha256", None)
    output["report_fingerprint_sha256"] = benchmark_fingerprint(body)
    validate_hollywood2_source_token_validation_report(output)
    return output
