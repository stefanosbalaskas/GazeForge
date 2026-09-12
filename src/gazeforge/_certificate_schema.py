"""Canonical schema guards shared by location-scale certificates."""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

from .exceptions import SchemaError

CERTIFICATE_FIELDS = frozenset(
    {
        "schema",
        "model",
        "model_fingerprint_sha256",
        "optimizer",
        "claim_boundary",
        "certificate_fingerprint_sha256",
    }
)
OPTIMIZER_FIELDS = frozenset(
    {"converged", "status", "message", "iterations"}
)


def require_exact_mapping_keys(
    value: Any,
    expected: Iterable[str],
    *,
    context: str,
) -> dict[str, Any]:
    """Require an ordinary mapping with exactly the canonical field set."""
    if not isinstance(value, dict):
        raise SchemaError(f"{context} must be a mapping.")
    expected_set = set(expected)
    actual_set = set(value)
    missing = sorted(expected_set - actual_set)
    unexpected = sorted(actual_set - expected_set)
    if missing or unexpected:
        details = []
        if missing:
            details.append(f"missing fields {missing}")
        if unexpected:
            details.append(f"unexpected fields {unexpected}")
        raise SchemaError(
            f"{context} has a noncanonical schema: "
            + "; ".join(details)
            + "."
        )
    return value


def require_canonical_optimizer(value: Any, *, context: str) -> dict[str, Any]:
    """Validate the exact optimizer metadata emitted by certificate builders."""
    optimizer = require_exact_mapping_keys(
        value,
        OPTIMIZER_FIELDS,
        context=f"{context} optimizer metadata",
    )
    if optimizer["converged"] is not True:
        raise SchemaError(f"Only converged {context} fits are certifiable.")
    status = optimizer["status"]
    if not isinstance(status, int) or isinstance(status, bool):
        raise SchemaError(f"{context} optimizer status must be an integer.")
    iterations = optimizer["iterations"]
    if (
        not isinstance(iterations, int)
        or isinstance(iterations, bool)
        or iterations < 0
    ):
        raise SchemaError(
            f"{context} optimizer iterations must be a non-negative integer."
        )
    if not isinstance(optimizer["message"], str):
        raise SchemaError(f"{context} optimizer message must be a string.")
    return optimizer


def require_finite_json_numbers(values: Iterable[Any], *, context: str) -> None:
    """Require finite built-in JSON numbers, rejecting bool/string coercion."""
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise SchemaError(
                f"{context} must contain only canonical JSON numbers."
            )
        if not math.isfinite(value):
            raise SchemaError(f"{context} contains a non-finite estimate.")
