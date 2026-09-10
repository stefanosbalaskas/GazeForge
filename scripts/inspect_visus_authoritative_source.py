#!/usr/bin/env python3
"""Inspect and manually review an authoritative VISUS source candidate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.visus_authoritative_source_certificate import (
    require_reviewed_visus_source_authority,
    validate_certificate_record,
)
from gazeforge.visus_authoritative_source_common import (
    REVIEW_RECORD_TYPE,
    review_fingerprint,
)
from gazeforge.visus_authoritative_source_intake import (
    inspect_visus_authoritative_source_candidate,
    validate_candidate_record,
)


def _load(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(f"Could not load VISUS {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise BenchmarkIntegrityError(f"VISUS {label} must contain one JSON object.")
    return value


def _write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _candidate(args: argparse.Namespace) -> int:
    candidate = inspect_visus_authoritative_source_candidate(
        args.root,
        args.source_artifact,
        args.rights_evidence,
        args.manifest,
    )
    validate_candidate_record(candidate)
    _write(args.output, candidate)
    print(
        json.dumps(
            {
                "candidate_fingerprint_sha256": candidate["candidate_fingerprint_sha256"],
                "file_count": candidate["inventory"]["file_count"],
                "source_authority_verified": candidate["review_boundary"][
                    "source_authority_verified"
                ],
                "source_audit_stage_authorized": candidate["review_boundary"][
                    "source_audit_stage_authorized"
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _review_template(args: argparse.Namespace) -> int:
    candidate = validate_candidate_record(_load(args.candidate, label="candidate"))
    review: dict[str, Any] = {
        "record_type": REVIEW_RECORD_TYPE,
        "decision": "pending",
        "candidate_fingerprint_sha256": candidate["candidate_fingerprint_sha256"],
        "reviewer": "REVIEW_REQUIRED",
        "reviewed_at": "REVIEW_REQUIRED",
        "source_authority_verified": False,
        "source_authority_evidence": "REVIEW_REQUIRED",
        "current_authoritative_distribution_identity_verified": False,
        "current_distribution_identity_evidence": "REVIEW_REQUIRED",
        "source_artifact_matches_authoritative_distribution_verified": False,
        "source_artifact_match_evidence": "REVIEW_REQUIRED",
        "extracted_tree_matches_source_artifact_verified": False,
        "extracted_tree_match_evidence": "REVIEW_REQUIRED",
        "rights_evidence_authoritative_verified": False,
        "rights_evidence_authority_evidence": "REVIEW_REQUIRED",
        "analysis_use_permitted_verified": False,
        "analysis_use_evidence": "REVIEW_REQUIRED",
        "redistribution_status_verified": "REVIEW_REQUIRED",
        "redistribution_evidence": "REVIEW_REQUIRED",
        "license_or_terms_identifier": "REVIEW_REQUIRED",
        "rights_scope_limited_to_reviewed_source": False,
        "participant_mapping_verified": False,
        "stimulus_mapping_verified": False,
        "coordinate_basis_verified": False,
        "timestamp_basis_verified": False,
        "independent_annotation_streams_verified": False,
        "empirical_validation_created": False,
        "raw_source_redistributed": False,
    }
    review["review_fingerprint_sha256"] = review_fingerprint(review)
    _write(args.output, review)
    print(
        json.dumps(
            {
                "candidate_fingerprint_sha256": candidate["candidate_fingerprint_sha256"],
                "decision": "pending",
                "review_fingerprint_sha256": review["review_fingerprint_sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _seal_review(args: argparse.Namespace) -> int:
    review = _load(args.review, label="review")
    if review.get("record_type") != REVIEW_RECORD_TYPE:
        raise BenchmarkIntegrityError("VISUS source-authority review type drifted.")
    review["review_fingerprint_sha256"] = review_fingerprint(review)
    _write(args.output, review)
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
    candidate = validate_candidate_record(_load(args.candidate, label="candidate"))
    reviewed = require_reviewed_visus_source_authority(
        args.root,
        args.source_artifact,
        args.rights_evidence,
        args.manifest,
        candidate,
        args.review,
    )
    certificate = validate_certificate_record(reviewed.certificate)
    _write(args.output, certificate)
    print(
        json.dumps(
            {
                "certificate_fingerprint_sha256": certificate[
                    "certificate_fingerprint_sha256"
                ],
                "source_audit_stage_authorized": certificate["authority_boundary"][
                    "source_audit_stage_authorized"
                ],
                "analysis_use_permitted": certificate["rights"]["analysis_use_permitted"],
                "redistribution_status": certificate["rights"]["redistribution_status"],
                "model_human_validation_created": certificate["scientific_boundary"][
                    "model_human_validation_created"
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _add_common_inputs(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("root", type=Path)
    parser.add_argument("source_artifact", type=Path)
    parser.add_argument("rights_evidence", type=Path)
    parser.add_argument("manifest", type=Path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build and review a fail-closed VISUS source-authority and rights certificate."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    candidate = subparsers.add_parser(
        "candidate",
        help="Bind exact source/tree/rights evidence without promoting source authority.",
    )
    _add_common_inputs(candidate)
    candidate.add_argument(
        "--output",
        type=Path,
        default=Path("visus-source-authority-candidate.json"),
    )
    candidate.set_defaults(func=_candidate)

    template = subparsers.add_parser(
        "review-template",
        help="Create a pending manual review bound to one candidate fingerprint.",
    )
    template.add_argument("candidate", type=Path)
    template.add_argument(
        "--output",
        type=Path,
        default=Path("visus-source-authority-review.json"),
    )
    template.set_defaults(func=_review_template)

    seal = subparsers.add_parser(
        "seal-review",
        help="Recompute the review fingerprint after human review edits.",
    )
    seal.add_argument("review", type=Path)
    seal.add_argument(
        "--output",
        type=Path,
        default=Path("visus-source-authority-review-sealed.json"),
    )
    seal.set_defaults(func=_seal_review)

    certificate = subparsers.add_parser(
        "certificate",
        help="Replay exact inputs and emit a non-empirical source-authority certificate.",
    )
    _add_common_inputs(certificate)
    certificate.add_argument("candidate", type=Path)
    certificate.add_argument("review", type=Path)
    certificate.add_argument(
        "--output",
        type=Path,
        default=Path("visus-source-authority-certificate.json"),
    )
    certificate.set_defaults(func=_certificate)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
