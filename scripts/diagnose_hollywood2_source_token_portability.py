#!/usr/bin/env python3
"""Diagnose full-report floating portability without relaxing any evidence gate.

This script is branch-diagnostic infrastructure. It reruns the existing aggregate Hollywood2
source-token validation, compares that raw aggregate report with one reviewed historical raw
aggregate report, and reports candidate metrics-only serialization identities across decimal
precisions. It does not declare any candidate precision reviewed or acceptable.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.hollywood2_token_validation import (
    load_hollywood2_source_token_analysis_authorization,
    run_hollywood2_source_token_validation,
    validate_hollywood2_source_token_validation_report,
)


def _round_metric_value(value: Any, decimal_places: int) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _round_metric_value(item, decimal_places)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_round_metric_value(item, decimal_places) for item in value]
    if isinstance(value, tuple):
        return [_round_metric_value(item, decimal_places) for item in value]
    if isinstance(value, (float, np.floating)):
        numeric = float(value)
        if not math.isfinite(numeric):
            raise ValueError("Diagnostic metrics must be finite.")
        return round(numeric, decimal_places)
    if isinstance(value, np.integer):
        return int(value)
    return value


def _diagnostic_canonicalize(report: dict[str, Any], decimal_places: int) -> dict[str, Any]:
    validated = validate_hollywood2_source_token_validation_report(report)
    output = copy.deepcopy(validated)
    output["metrics"] = _round_metric_value(output["metrics"], decimal_places)
    output["protocol"]["numeric_canonicalization"] = {
        "method": "recursive_round_finite_metric_floats",
        "metric_float_decimal_places": decimal_places,
        "nonfinite_metric_floats_permitted": False,
        "benchmark_model_protocol_numeric_values_rounded": False,
    }
    body = dict(output)
    body.pop("report_fingerprint_sha256", None)
    output["report_fingerprint_sha256"] = benchmark_fingerprint(body)
    return output


def _canonical_text(report: dict[str, Any]) -> str:
    return (
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    )


def _max_metric_delta(first: Any, second: Any, path: str = "metrics") -> tuple[float, str]:
    if isinstance(first, dict):
        if not isinstance(second, dict) or set(first) != set(second):
            raise AssertionError(f"metric structure drift at {path}")
        best = (0.0, path)
        for key in first:
            candidate = _max_metric_delta(first[key], second[key], f"{path}.{key}")
            if candidate[0] > best[0]:
                best = candidate
        return best
    if isinstance(first, list):
        if not isinstance(second, list) or len(first) != len(second):
            raise AssertionError(f"metric list structure drift at {path}")
        best = (0.0, path)
        for index, (item_first, item_second) in enumerate(zip(first, second, strict=True)):
            candidate = _max_metric_delta(
                item_first,
                item_second,
                f"{path}[{index}]",
            )
            if candidate[0] > best[0]:
                best = candidate
        return best
    if isinstance(first, float):
        if not isinstance(second, float):
            raise AssertionError(f"metric scalar type drift at {path}")
        if not math.isfinite(first) or not math.isfinite(second):
            raise AssertionError(f"non-finite metric at {path}")
        return abs(first - second), path
    if type(first) is not type(second) or first != second:
        raise AssertionError(f"non-float metric drift at {path}: {first!r} != {second!r}")
    return 0.0, path


def _strip_expected_variants(report: dict[str, Any]) -> dict[str, Any]:
    output = copy.deepcopy(report)
    output.pop("report_fingerprint_sha256", None)
    protocol = output.get("protocol")
    if isinstance(protocol, dict):
        protocol.pop("numeric_canonicalization", None)
    output.pop("metrics", None)
    return output


def _file_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--reviewed-raw", type=Path, required=True)
    parser.add_argument(
        "--authorization",
        default=(
            "validation/governance/"
            "hollywood2-source-token-analysis-authorization-v1.json"
        ),
    )
    parser.add_argument(
        "--raw-output",
        type=Path,
        default=Path("hollywood2-source-token-live-raw-diagnostic.json"),
    )
    parser.add_argument(
        "--diagnostic-output",
        type=Path,
        default=Path("hollywood2-source-token-portability-diagnostic.json"),
    )
    args = parser.parse_args()

    reviewed_bytes = args.reviewed_raw.read_bytes()
    reviewed = validate_hollywood2_source_token_validation_report(
        json.loads(reviewed_bytes)
    )

    authorization = load_hollywood2_source_token_analysis_authorization(
        args.authorization
    )
    run = run_hollywood2_source_token_validation(
        args.source_root,
        authorization,
        target_sampling_rate_hz=60.0,
        min_label_purity=0.75,
        n_splits=4,
        ivt_velocity_threshold_px_s=1000.0,
        random_state=42,
        n_estimators=100,
        context_radius_ms=50.0,
        rolling_window_ms=80.0,
        hidden_layer_sizes=(32, 16),
        temporal_max_iter=50,
    )
    live = validate_hollywood2_source_token_validation_report(run.report)

    args.raw_output.write_text(_canonical_text(live), encoding="utf-8")

    if _strip_expected_variants(reviewed) != _strip_expected_variants(live):
        raise AssertionError(
            "Non-metric Hollywood2 report content drifted; numeric portability is not sufficient."
        )

    max_delta, max_delta_path = _max_metric_delta(reviewed["metrics"], live["metrics"])
    candidates: list[dict[str, Any]] = []
    narrowest_match: int | None = None
    for places in (15, 14, 13, 12, 11, 10):
        reviewed_candidate = _diagnostic_canonicalize(reviewed, places)
        live_candidate = _diagnostic_canonicalize(live, places)
        reviewed_text = _canonical_text(reviewed_candidate)
        live_text = _canonical_text(live_candidate)
        fingerprint_match = (
            reviewed_candidate["report_fingerprint_sha256"]
            == live_candidate["report_fingerprint_sha256"]
        )
        file_match = reviewed_text == live_text
        candidate = {
            "metric_float_decimal_places": places,
            "reviewed_report_fingerprint_sha256": reviewed_candidate[
                "report_fingerprint_sha256"
            ],
            "live_report_fingerprint_sha256": live_candidate[
                "report_fingerprint_sha256"
            ],
            "reviewed_report_file_sha256": _file_sha(reviewed_text),
            "live_report_file_sha256": _file_sha(live_text),
            "fingerprint_match": fingerprint_match,
            "file_bytes_match": file_match,
        }
        candidates.append(candidate)
        if fingerprint_match and file_match and narrowest_match is None:
            narrowest_match = places

    diagnostic = {
        "record_type": "hollywood2-source-token-portability-diagnostic",
        "reviewed_raw_report_fingerprint_sha256": reviewed[
            "report_fingerprint_sha256"
        ],
        "reviewed_raw_report_file_sha256": hashlib.sha256(reviewed_bytes).hexdigest(),
        "live_raw_report_fingerprint_sha256": live["report_fingerprint_sha256"],
        "live_raw_report_file_sha256": hashlib.sha256(
            args.raw_output.read_bytes()
        ).hexdigest(),
        "max_abs_raw_metric_delta": max_delta,
        "max_abs_raw_metric_delta_path": max_delta_path,
        "candidate_serializations": candidates,
        "highest_precision_candidate_with_exact_full_report_match": narrowest_match,
        "scientific_boundary": {
            "diagnostic_only": True,
            "candidate_contract_reviewed": False,
            "participant_identity_mapping_verified": False,
            "participant_generalization_claim": False,
            "cross_dataset_validation_created": False,
            "raw_source_redistributed_by_gazeforge": False,
        },
    }
    args.diagnostic_output.write_text(
        json.dumps(diagnostic, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(diagnostic, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
