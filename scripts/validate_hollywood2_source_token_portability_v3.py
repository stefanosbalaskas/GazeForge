#!/usr/bin/env python3
"""Replay and live-bind the Hollywood2 source-token v3 portability contract."""

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
    HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V3,
    canonicalize_hollywood2_source_token_validation_report,
)
from gazeforge.hollywood2_token_portability_evidence import (
    validate_hollywood2_source_token_portability_evidence,
)
from gazeforge.hollywood2_token_portability_v3_evidence import (
    V3_CANONICAL_REPORT_FILE_SHA256,
    V3_CANONICAL_REPORT_FINGERPRINT,
    validate_hollywood2_source_token_portability_v3_evidence,
)
from gazeforge.hollywood2_token_validation import (
    validate_hollywood2_source_token_validation_report,
)

DEFAULT_FROZEN = Path(
    "validation/evidence/hollywood2/"
    "hollywood2-source-token-60hz-frozen-summary-v1.json"
)
DEFAULT_V2_EVIDENCE = Path(
    "validation/evidence/hollywood2/"
    "hollywood2-source-token-numeric-portability-evidence-v2.json"
)
DEFAULT_V3_EVIDENCE = Path(
    "validation/evidence/hollywood2/"
    "hollywood2-source-token-numeric-portability-evidence-v3.json"
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
    assert boundary["cross_dataset_validation_created"] is False
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
    v2_evidence_path: Path = DEFAULT_V2_EVIDENCE,
    v3_evidence_path: Path = DEFAULT_V3_EVIDENCE,
) -> None:
    """Replay v1, v2, and v3 from both original reviewed raw artifacts."""
    frozen = load_frozen_benchmark_report(frozen_path)
    v2_evidence = validate_hollywood2_source_token_portability_evidence(v2_evidence_path)
    v3_evidence = validate_hollywood2_source_token_portability_v3_evidence(
        v3_evidence_path
    )
    reviewed = v3_evidence["reviewed_source_verified_artifacts"]

    v1_expected = v2_evidence["migration"]["from_contract"]
    v2_expected = v2_evidence["migration"]["to_contract"]
    v3_expected = v3_evidence["migration"]["to_contract"]

    v1_texts: list[str] = []
    v2_texts: list[str] = []
    v3_texts: list[str] = []
    for label, path, evidence_key in (
        ("pre-merge", pre_report_path, "pre_merge"),
        ("exact-merge", merge_report_path, "exact_merge"),
    ):
        raw = _load_raw_reviewed_report(path, reviewed[evidence_key])
        v1, v1_text = _canonicalize_and_bind(
            raw,
            contract=HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V1,
            expected_fingerprint=v1_expected[
                "canonical_source_report_fingerprint_sha256"
            ],
            expected_file_sha256=v1_expected["canonical_source_report_file_sha256"],
        )
        v2, v2_text = _canonicalize_and_bind(
            raw,
            contract=HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V2,
            expected_fingerprint=v2_expected[
                "canonical_source_report_fingerprint_sha256"
            ],
            expected_file_sha256=v2_expected["canonical_source_report_file_sha256"],
        )
        v3, v3_text = _canonicalize_and_bind(
            raw,
            contract=HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V3,
            expected_fingerprint=v3_expected[
                "canonical_source_report_fingerprint_sha256"
            ],
            expected_file_sha256=v3_expected["canonical_source_report_file_sha256"],
        )

        assert v1["benchmark"] == frozen["benchmark"] == v2["benchmark"] == v3["benchmark"]
        assert v1["model"] == frozen["model"] == v2["model"] == v3["model"]
        assert v1["protocol"]["preparation"] == frozen["protocol"]["preparation"]
        assert v2["protocol"]["preparation"] == frozen["protocol"]["preparation"]
        assert v3["protocol"]["preparation"] == frozen["protocol"]["preparation"]
        assert v1["metrics"]["analysis_label_counts"] == frozen["metrics"][
            "analysis_label_counts"
        ]
        assert v1["metrics"]["source_token_fold_assignment"] == frozen["metrics"][
            "source_token_fold_assignment"
        ]
        _assert_no_promotion(v3, v3_text)

        v1_texts.append(v1_text)
        v2_texts.append(v2_text)
        v3_texts.append(v3_text)
        print(label, "v1 fingerprint:", v1["report_fingerprint_sha256"])
        print(label, "v2 fingerprint:", v2["report_fingerprint_sha256"])
        print(label, "v3 fingerprint:", v3["report_fingerprint_sha256"])

    assert v1_texts[0] == v1_texts[1]
    assert v2_texts[0] == v2_texts[1]
    assert v3_texts[0] == v3_texts[1]
    assert v1_texts[0] != v2_texts[0]
    assert v2_texts[0] != v3_texts[0]
    assert v3_evidence["reviewed_source_verified_artifacts"][
        "v3_recanonicalized_reviewed_reports_byte_identical"
    ] is True
    assert frozen["report_fingerprint_sha256"] == (
        v3_evidence["historical_evidence"][
            "v1_frozen_summary_report_fingerprint_sha256"
        ]
    )
    print("v1 and v2 evidence preserved; v3 reviewed artifacts are byte-identical")
    print("v3 reviewed full-report fingerprint:", V3_CANONICAL_REPORT_FINGERPRINT)


def bind_live_v3_report(
    report_path: Path,
    *,
    frozen_path: Path = DEFAULT_FROZEN,
    v3_evidence_path: Path = DEFAULT_V3_EVIDENCE,
) -> None:
    """Fail closed unless a live aggregate report exactly reproduces the v3 identity."""
    report = validate_hollywood2_source_token_validation_report(report_path)
    frozen = load_frozen_benchmark_report(frozen_path)
    evidence = validate_hollywood2_source_token_portability_v3_evidence(v3_evidence_path)
    expected = evidence["migration"]["to_contract"]
    text = report_path.read_text(encoding="utf-8")

    protocol = report["protocol"]
    preparation = protocol["preparation"]
    inventory = preparation["inventory"]
    frozen_preparation = frozen["protocol"]["preparation"]

    assert protocol["numeric_canonicalization"] == (
        HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V3
    )
    assert report["report_fingerprint_sha256"] == V3_CANONICAL_REPORT_FINGERPRINT
    assert report["report_fingerprint_sha256"] == (
        expected["canonical_source_report_fingerprint_sha256"]
    )
    observed_file_sha = hashlib.sha256(report_path.read_bytes()).hexdigest()
    assert observed_file_sha == V3_CANONICAL_REPORT_FILE_SHA256
    assert observed_file_sha == expected["canonical_source_report_file_sha256"]

    assert report["benchmark"] == frozen["benchmark"]
    assert report["model"] == frozen["model"]
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
    assert report["metrics"]["analysis_label_counts"] == frozen["metrics"][
        "analysis_label_counts"
    ]
    assert report["metrics"]["source_token_fold_assignment"] == frozen["metrics"][
        "source_token_fold_assignment"
    ]
    _assert_no_promotion(report, text)

    print("v3 canonical report fingerprint:", report["report_fingerprint_sha256"])
    print("v3 canonical report file sha256:", observed_file_sha)
    print("v1 frozen scientific summary preserved:", frozen["report_fingerprint_sha256"])
    print("claim boundary: source-token-held-out only")


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    replay = subparsers.add_parser("replay")
    replay.add_argument("--pre-report", type=Path, required=True)
    replay.add_argument("--merge-report", type=Path, required=True)
    replay.add_argument("--frozen", type=Path, default=DEFAULT_FROZEN)
    replay.add_argument("--v2-evidence", type=Path, default=DEFAULT_V2_EVIDENCE)
    replay.add_argument("--v3-evidence", type=Path, default=DEFAULT_V3_EVIDENCE)

    live = subparsers.add_parser("bind-live")
    live.add_argument("--report", type=Path, required=True)
    live.add_argument("--frozen", type=Path, default=DEFAULT_FROZEN)
    live.add_argument("--v3-evidence", type=Path, default=DEFAULT_V3_EVIDENCE)

    args = parser.parse_args()
    if args.command == "replay":
        replay_reviewed_artifacts(
            args.pre_report,
            args.merge_report,
            frozen_path=args.frozen,
            v2_evidence_path=args.v2_evidence,
            v3_evidence_path=args.v3_evidence,
        )
    else:
        bind_live_v3_report(
            args.report,
            frozen_path=args.frozen,
            v3_evidence_path=args.v3_evidence,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
