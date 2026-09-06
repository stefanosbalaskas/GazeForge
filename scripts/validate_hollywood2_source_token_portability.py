#!/usr/bin/env python3
"""Validate Hollywood2 source-token v1→v2 portability evidence and live reports."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from gazeforge.dashboard import load_frozen_benchmark_report
from gazeforge.hollywood2_token_evidence import (
    HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V1,
    HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V2,
    canonicalize_hollywood2_source_token_validation_report,
)
from gazeforge.hollywood2_token_portability_evidence import (
    validate_hollywood2_source_token_portability_evidence,
    validate_hollywood2_v1_v2_metric_equivalence,
)
from gazeforge.hollywood2_token_validation import (
    validate_hollywood2_source_token_validation_report,
)

DEFAULT_FROZEN = Path(
    "validation/evidence/hollywood2/"
    "hollywood2-source-token-60hz-frozen-summary-v1.json"
)
DEFAULT_PORTABILITY_EVIDENCE = Path(
    "validation/evidence/hollywood2/"
    "hollywood2-source-token-numeric-portability-evidence-v2.json"
)
METRIC_KEYS = (
    "analysis_label_counts",
    "source_token_fold_assignment",
    "summary",
)


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


def _assert_no_promotion(report: dict[str, Any], text: str) -> None:
    protocol = report["protocol"]
    boundary = protocol["scientific_boundary"]
    preparation = protocol["preparation"]
    assert boundary["participant_identity_mapping_verified"] is False
    assert boundary["participant_disjoint_validation_created"] is False
    assert boundary["participant_generalization_claim"] is False
    assert boundary["raw_source_redistributed_by_gazeforge"] is False
    assert boundary["raw_predictions_embedded"] is False
    assert preparation["participant_identity_resolved"] is False
    assert preparation["raw_source_rows_embedded"] is False
    assert preparation["source_filenames_embedded"] is False
    assert ".arff" not in text
    assert "_hollywood2_em" not in text


def _load_raw_reviewed_report(
    path: Path,
    lineage: dict[str, Any],
) -> dict[str, Any]:
    raw_bytes = path.read_bytes()
    assert hashlib.sha256(raw_bytes).hexdigest() == (
        lineage["uncanonicalized_report_file_sha256"]
    )
    raw = validate_hollywood2_source_token_validation_report(json.loads(raw_bytes))
    assert raw["report_fingerprint_sha256"] == (
        lineage["uncanonicalized_report_fingerprint_sha256"]
    )
    return raw


def _canonicalize_and_bind(
    raw: dict[str, Any],
    *,
    contract: dict[str, Any],
    expected_fingerprint: str,
    expected_file_sha256: str,
) -> tuple[dict[str, Any], str]:
    report = canonicalize_hollywood2_source_token_validation_report(
        raw,
        numeric_canonicalization=contract,
    )
    text = _canonical_text(report)
    assert report["report_fingerprint_sha256"] == expected_fingerprint
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == expected_file_sha256
    return report, text


def replay_reviewed_artifacts(
    pre_report_path: Path,
    merge_report_path: Path,
    *,
    frozen_path: Path = DEFAULT_FROZEN,
    evidence_path: Path = DEFAULT_PORTABILITY_EVIDENCE,
) -> None:
    frozen = load_frozen_benchmark_report(frozen_path)
    evidence = validate_hollywood2_source_token_portability_evidence(evidence_path)
    reviewed = evidence["reviewed_source_verified_artifacts"]
    before = evidence["migration"]["from_contract"]
    after = evidence["migration"]["to_contract"]

    v1_texts: list[str] = []
    v2_texts: list[str] = []
    for label, path, evidence_key in (
        ("pre-merge", pre_report_path, "pre_merge"),
        ("exact-merge", merge_report_path, "exact_merge"),
    ):
        raw = _load_raw_reviewed_report(path, reviewed[evidence_key])
        v1, v1_text = _canonicalize_and_bind(
            raw,
            contract=HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V1,
            expected_fingerprint=before["canonical_source_report_fingerprint_sha256"],
            expected_file_sha256=before["canonical_source_report_file_sha256"],
        )
        v2, v2_text = _canonicalize_and_bind(
            raw,
            contract=HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V2,
            expected_fingerprint=after["canonical_source_report_fingerprint_sha256"],
            expected_file_sha256=after["canonical_source_report_file_sha256"],
        )

        assert v1["benchmark"] == frozen["benchmark"] == v2["benchmark"]
        assert v1["model"] == frozen["model"] == v2["model"]
        for key in METRIC_KEYS:
            assert v1["metrics"][key] == frozen["metrics"][key]
            validate_hollywood2_v1_v2_metric_equivalence(
                v1["metrics"][key],
                v2["metrics"][key],
            )
        _assert_no_promotion(v2, v2_text)

        v1_texts.append(v1_text)
        v2_texts.append(v2_text)
        print(label, "v1 fingerprint:", v1["report_fingerprint_sha256"])
        print(label, "v2 fingerprint:", v2["report_fingerprint_sha256"])

    assert v1_texts[0] == v1_texts[1]
    assert v2_texts[0] == v2_texts[1]
    assert v1_texts[0] != v2_texts[0]
    assert reviewed["v2_recanonicalized_reports_byte_identical"] is True
    assert frozen["report_fingerprint_sha256"] == (
        before["frozen_summary_report_fingerprint_sha256"]
    )
    print("v1 evidence preserved and v2 reviewed artifacts are byte-identical")
    print("this is artifact replay, not a fresh source rerun")


def bind_live_v2_report(
    report_path: Path,
    *,
    frozen_path: Path = DEFAULT_FROZEN,
    evidence_path: Path = DEFAULT_PORTABILITY_EVIDENCE,
) -> None:
    report = validate_hollywood2_source_token_validation_report(report_path)
    frozen = load_frozen_benchmark_report(frozen_path)
    evidence = validate_hollywood2_source_token_portability_evidence(evidence_path)
    expected = evidence["migration"]["to_contract"]
    text = report_path.read_text(encoding="utf-8")

    protocol = report["protocol"]
    preparation = protocol["preparation"]
    inventory = preparation["inventory"]
    frozen_preparation = frozen["protocol"]["preparation"]

    assert protocol["numeric_canonicalization"] == (
        HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V2
    )
    assert report["report_fingerprint_sha256"] == (
        expected["canonical_source_report_fingerprint_sha256"]
    )
    assert hashlib.sha256(report_path.read_bytes()).hexdigest() == (
        expected["canonical_source_report_file_sha256"]
    )
    assert report["benchmark"] == frozen["benchmark"]
    assert report["model"] == frozen["model"]
    for key in METRIC_KEYS:
        validate_hollywood2_v1_v2_metric_equivalence(
            frozen["metrics"][key],
            report["metrics"][key],
        )

    assert preparation["analysis_rows"] == frozen_preparation["analysis_rows"]
    assert preparation["analysis_sampling_rate_hz"] == (
        frozen_preparation["analysis_sampling_rate_hz"]
    )
    assert preparation["prepared_rows_before_exclusions"] == (
        frozen_preparation["prepared_rows_before_exclusions"]
    )
    assert preparation["excluded_rows"] == frozen_preparation["excluded_rows"]
    assert inventory["ground_truth_file_count"] == (
        frozen_preparation["ground_truth_file_count"]
    )
    assert inventory["ground_truth_sample_count"] == (
        frozen_preparation["ground_truth_sample_count"]
    )
    assert inventory["source_tokens"] == frozen_preparation["source_tokens"]
    assert inventory["source_token_count"] == frozen_preparation["source_token_count"]
    _assert_no_promotion(report, text)

    print("v2 canonical report fingerprint:", report["report_fingerprint_sha256"])
    print(
        "v2 canonical report file sha256:",
        hashlib.sha256(report_path.read_bytes()).hexdigest(),
    )
    print("v1 frozen scientific summary preserved:", frozen["report_fingerprint_sha256"])
    print("claim boundary: source-token-held-out only")


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    replay = subparsers.add_parser("replay")
    replay.add_argument("--pre-report", type=Path, required=True)
    replay.add_argument("--merge-report", type=Path, required=True)
    replay.add_argument("--frozen", type=Path, default=DEFAULT_FROZEN)
    replay.add_argument("--evidence", type=Path, default=DEFAULT_PORTABILITY_EVIDENCE)

    live = subparsers.add_parser("bind-live")
    live.add_argument("--report", type=Path, required=True)
    live.add_argument("--frozen", type=Path, default=DEFAULT_FROZEN)
    live.add_argument("--evidence", type=Path, default=DEFAULT_PORTABILITY_EVIDENCE)

    args = parser.parse_args()
    if args.command == "replay":
        replay_reviewed_artifacts(
            args.pre_report,
            args.merge_report,
            frozen_path=args.frozen,
            evidence_path=args.evidence,
        )
    else:
        bind_live_v2_report(
            args.report,
            frozen_path=args.frozen,
            evidence_path=args.evidence,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
