"""Deterministic publication layer for Hollywood2 source-token validation reports.

The underlying model comparison uses ordinary floating-point arithmetic. Independent reruns can
therefore differ in the last machine-representable bits of aggregate calibration metrics even when
the held-out rows, predictions, folds, and scientifically meaningful results are unchanged. Frozen
evidence needs a stricter serialization contract than that.

This module applies a deliberately narrow canonicalization only to finite floating-point values in
the report ``metrics`` object before the publication fingerprint is computed. Benchmark metadata,
model configuration, protocol settings, source identities, and scientific claim boundaries are not
rounded or rewritten.
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

HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES = 15
HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION = {
    "method": "recursive_round_finite_metric_floats",
    "metric_float_decimal_places": HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES,
    "nonfinite_metric_floats_permitted": False,
    "benchmark_model_protocol_numeric_values_rounded": False,
}


def _canonicalize_metric_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _canonicalize_metric_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_canonicalize_metric_value(item) for item in value]
    if isinstance(value, tuple):
        return [_canonicalize_metric_value(item) for item in value]
    if isinstance(value, (float, np.floating)):
        numeric = float(value)
        if not math.isfinite(numeric):
            raise BenchmarkIntegrityError(
                "Hollywood2 frozen metrics must not contain non-finite floating-point values."
            )
        return round(numeric, HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES)
    if isinstance(value, np.integer):
        return int(value)
    return value


def canonicalize_hollywood2_source_token_validation_report(
    report: dict[str, Any],
) -> dict[str, Any]:
    """Return a fingerprint-stable publication copy of a validated source-token report.

    Only the ``metrics`` subtree is numerically canonicalized. A protocol declaration records the
    exact rule, then the report fingerprint is recomputed and the complete Hollywood2 scientific
    claim boundary is revalidated.
    """
    validated = validate_hollywood2_source_token_validation_report(report)
    output = copy.deepcopy(validated)
    metrics = output.get("metrics")
    protocol = output.get("protocol")
    if not isinstance(metrics, dict) or not isinstance(protocol, dict):
        raise BenchmarkIntegrityError(
            "Hollywood2 source-token report is missing metrics or protocol metadata."
        )

    output["metrics"] = _canonicalize_metric_value(metrics)
    protocol["numeric_canonicalization"] = dict(
        HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION
    )

    body = dict(output)
    body.pop("report_fingerprint_sha256", None)
    output["report_fingerprint_sha256"] = benchmark_fingerprint(body)
    validate_hollywood2_source_token_validation_report(output)
    return output
