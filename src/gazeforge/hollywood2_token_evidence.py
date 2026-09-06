"""Deterministic publication layer for Hollywood2 source-token validation reports.

The underlying model comparison uses ordinary floating-point arithmetic. Independent reruns can
therefore differ in the last machine-representable bits of aggregate metrics even when the held-out
rows, folds, source identities, predictions, and scientifically meaningful results are unchanged.
Frozen evidence needs an explicit serialization contract for those finite metric floats.

Version 1 rounded finite values in the ``metrics`` subtree to 15 decimal places. That contract is
retained for historical replay. Version 2 rounds the same metrics-only subtree to 14 decimal places
after exact-software reruns demonstrated last-bit hardware/BLAS portability drift at 15 places.
Benchmark metadata, model configuration, protocol settings, source identities, and scientific claim
boundaries are never rounded or rewritten by either contract.
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

# Public aliases identify the current publication contract. Historical validation must import the
# explicit V1 names above rather than relying on these aliases.
HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES = (
    HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES_V2
)
HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION = dict(
    HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V2
)


def _validate_numeric_canonicalization_contract(
    contract: dict[str, Any],
) -> dict[str, Any]:
    if contract not in (
        HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V1,
        HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V2,
    ):
        raise BenchmarkIntegrityError(
            "Hollywood2 numeric canonicalization must use the reviewed v1 or v2 contract."
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
    }:
        raise BenchmarkIntegrityError(
            "Hollywood2 metric canonicalization supports only reviewed 14- or 15-place contracts."
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

    The default is the current v2 portability contract. Pass
    ``HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V1`` explicitly to replay historical v1
    publication evidence.
    """
    validated = validate_hollywood2_source_token_validation_report(report)
    output = copy.deepcopy(validated)
    metrics = output.get("metrics")
    protocol = output.get("protocol")
    if not isinstance(metrics, dict) or not isinstance(protocol, dict):
        raise BenchmarkIntegrityError(
            "Hollywood2 source-token report is missing metrics or protocol metadata."
        )

    contract = _validate_numeric_canonicalization_contract(
        numeric_canonicalization
        or HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V2
    )
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
