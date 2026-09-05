#!/usr/bin/env python3
"""Execute aggregate Hollywood2EM source-token validation on an external canonical checkout."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from gazeforge.hollywood2_token_evidence import (
    canonicalize_hollywood2_source_token_validation_report,
)
from gazeforge.hollywood2_token_validation import (
    load_hollywood2_source_token_analysis_authorization,
    run_hollywood2_source_token_validation,
    validate_hollywood2_source_token_validation_report,
)


def _summary(report: dict[str, object]) -> dict[str, object]:
    metrics = report["metrics"]
    protocol = report["protocol"]
    assert isinstance(metrics, dict)
    assert isinstance(protocol, dict)
    preparation = protocol["preparation"]
    boundary = protocol["scientific_boundary"]
    assert isinstance(preparation, dict)
    assert isinstance(boundary, dict)
    return {
        "report_fingerprint_sha256": report["report_fingerprint_sha256"],
        "analysis_rows": preparation["analysis_rows"],
        "source_tokens": preparation["inventory"]["source_tokens"],
        "analysis_sampling_rate_hz": preparation["analysis_sampling_rate_hz"],
        "models": report["model"]["models"],
        "summary": metrics["summary"],
        "participant_identity_mapping_verified": boundary[
            "participant_identity_mapping_verified"
        ],
        "participant_generalization_claim": boundary["participant_generalization_claim"],
        "raw_source_redistributed_by_gazeforge": boundary[
            "raw_source_redistributed_by_gazeforge"
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True)
    parser.add_argument(
        "--authorization",
        default=(
            "validation/governance/"
            "hollywood2-source-token-analysis-authorization-v1.json"
        ),
    )
    parser.add_argument(
        "--output",
        default="hollywood2-source-token-validation-v1.json",
    )
    parser.add_argument("--target-rate-hz", type=float, default=60.0)
    parser.add_argument("--min-label-purity", type=float, default=0.75)
    parser.add_argument("--folds", type=int, default=4)
    parser.add_argument("--ivt-threshold-px-s", type=float, default=1000.0)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--rf-trees", type=int, default=100)
    parser.add_argument("--context-radius-ms", type=float, default=50.0)
    parser.add_argument("--rolling-window-ms", type=float, default=80.0)
    parser.add_argument("--context-hidden", default="32,16")
    parser.add_argument("--context-max-iter", type=int, default=50)
    args = parser.parse_args()

    hidden = tuple(
        int(value.strip())
        for value in str(args.context_hidden).split(",")
        if value.strip()
    )
    if not hidden:
        parser.error("--context-hidden must contain at least one positive layer size")
    if any(value <= 0 for value in hidden):
        parser.error("--context-hidden layer sizes must be positive")

    authorization = load_hollywood2_source_token_analysis_authorization(
        args.authorization
    )
    run = run_hollywood2_source_token_validation(
        args.source_root,
        authorization,
        target_sampling_rate_hz=args.target_rate_hz,
        min_label_purity=args.min_label_purity,
        n_splits=args.folds,
        ivt_velocity_threshold_px_s=args.ivt_threshold_px_s,
        random_state=args.random_state,
        n_estimators=args.rf_trees,
        context_radius_ms=args.context_radius_ms,
        rolling_window_ms=args.rolling_window_ms,
        hidden_layer_sizes=hidden,
        temporal_max_iter=args.context_max_iter,
    )
    report = canonicalize_hollywood2_source_token_validation_report(run.report)
    report = validate_hollywood2_source_token_validation_report(report)
    output = Path(args.output)
    output.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(_summary(report), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
