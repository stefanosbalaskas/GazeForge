#!/usr/bin/env python3
"""Inspect and review an explicit Hollywood2 participant crosswalk."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.hollywood2_explicit_crosswalk_certificate import (
    validate_certificate_record,
)
from gazeforge.hollywood2_explicit_crosswalk_intake import (
    REVIEW_RECORD_TYPE,
    candidate_fingerprint,
    inspect_explicit_crosswalk_candidate,
    require_reviewed_explicit_crosswalk,
    review_fingerprint,
    validate_candidate_record,
)


def _load_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(f"Could not load {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise BenchmarkIntegrityError(f"{label} must contain one JSON object.")
    return value


def _write_object(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _candidate(args: argparse.Namespace) -> int:
    candidate = inspect_explicit_crosswalk_candidate(args.source, args.manifest)
    validate_candidate_record(candidate)
    _write_object(args.output, candidate)
    summary = {
        "candidate_fingerprint_sha256": candidate["candidate_fingerprint_sha256"],
        "complete_gin_token_coverage": candidate["mapping_summary"][
            "complete_gin_token_coverage"
        ],
        "entry_count": candidate["mapping_summary"]["entry_count"],
        "participant_identity_mapping_verified": candidate["review_boundary"][
            "participant_identity_mapping_verified"
        ],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def _review_template(args: argparse.Namespace) -> int:
    candidate = validate_candidate_record(_load_object(args.candidate, label="candidate"))
    template: dict[str, Any] = {
        "record_type": REVIEW_RECORD_TYPE,
        "decision": "pending",
        "candidate_fingerprint_sha256": candidate["candidate_fingerprint_sha256"],
        "reviewer": "REVIEW_REQUIRED",
        "reviewed_at": "REVIEW_REQUIRED",
        "source_authority_verified": False,
        "source_authority_evidence": "REVIEW_REQUIRED",
        "mapping_explicit_in_source_verified": False,
        "mapping_explicitness_evidence": "REVIEW_REQUIRED",
        "mapping_transcription_verified": False,
        "mapping_transcription_evidence": "REVIEW_REQUIRED",
        "task_group_semantics_verified": False,
        "task_group_semantics_evidence": "REVIEW_REQUIRED",
        "source_version_scope_verified": False,
        "source_version_scope_evidence": "REVIEW_REQUIRED",
        "rights_scope_promoted": False,
        "empirical_validation_created": False,
    }
    template["review_fingerprint_sha256"] = review_fingerprint(template)
    _write_object(args.output, template)
    print(
        json.dumps(
            {
                "candidate_fingerprint_sha256": candidate["candidate_fingerprint_sha256"],
                "decision": "pending",
                "review_fingerprint_sha256": template["review_fingerprint_sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _seal_review(args: argparse.Namespace) -> int:
    review = _load_object(args.review, label="review")
    if review.get("record_type") != REVIEW_RECORD_TYPE:
        raise BenchmarkIntegrityError("Hollywood2 crosswalk review record type drifted.")
    review["review_fingerprint_sha256"] = review_fingerprint(review)
    _write_object(args.output, review)
    print(
        json.dumps(
            {
                "decision": review.get("decision"),
                "review_fingerprint_sha256": review["review_fingerprint_sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _certificate(args: argparse.Namespace) -> int:
    candidate = validate_candidate_record(_load_object(args.candidate, label="candidate"))
    if candidate["candidate_fingerprint_sha256"] != candidate_fingerprint(candidate):
        raise BenchmarkIntegrityError("Hollywood2 crosswalk candidate fingerprint drifted.")
    reviewed = require_reviewed_explicit_crosswalk(
        args.source,
        args.manifest,
        candidate,
        args.review,
    )
    certificate = validate_certificate_record(reviewed.certificate)
    _write_object(args.output, certificate)
    summary = {
        "certificate_fingerprint_sha256": certificate["certificate_fingerprint_sha256"],
        "mapping_fingerprint_sha256": certificate["mapping_fingerprint_sha256"],
        "participant_identity_mapping_verified": certificate["mapping_boundary"][
            "participant_identity_mapping_verified"
        ],
        "token_count": certificate["token_count"],
        "cross_dataset_validation_created": certificate["scientific_boundary"][
            "cross_dataset_validation_created"
        ],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build and review a privacy-preserving Hollywood2 explicit participant crosswalk."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    candidate = subparsers.add_parser(
        "candidate",
        help="Inspect an explicit source + transcription without promoting participant identity.",
    )
    candidate.add_argument("source", type=Path)
    candidate.add_argument("manifest", type=Path)
    candidate.add_argument(
        "--output",
        type=Path,
        default=Path("hollywood2-crosswalk-candidate.json"),
    )
    candidate.set_defaults(func=_candidate)

    template = subparsers.add_parser(
        "review-template",
        help="Create a pending manual review template bound to one candidate fingerprint.",
    )
    template.add_argument("candidate", type=Path)
    template.add_argument(
        "--output",
        type=Path,
        default=Path("hollywood2-crosswalk-review.json"),
    )
    template.set_defaults(func=_review_template)

    seal = subparsers.add_parser(
        "seal-review",
        help="Recompute the fingerprint after the human reviewer edits the review record.",
    )
    seal.add_argument("review", type=Path)
    seal.add_argument(
        "--output",
        type=Path,
        default=Path("hollywood2-crosswalk-review-sealed.json"),
    )
    seal.set_defaults(func=_seal_review)

    certificate = subparsers.add_parser(
        "certificate",
        help="Validate the approved review and emit a non-empirical mapping certificate.",
    )
    certificate.add_argument("source", type=Path)
    certificate.add_argument("manifest", type=Path)
    certificate.add_argument("candidate", type=Path)
    certificate.add_argument("review", type=Path)
    certificate.add_argument(
        "--output",
        type=Path,
        default=Path("hollywood2-crosswalk-certificate.json"),
    )
    certificate.set_defaults(func=_certificate)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
