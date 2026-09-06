"""JSON-only CLI for Gaze-in-the-Wild first-party archive/rights resolution evidence."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

from .gaze_in_wild_first_party_resolution import (
    build_gaze_in_wild_first_party_resolution_request,
    build_gaze_in_wild_first_party_resolution_response_scaffold,
    validate_gaze_in_wild_first_party_resolution_request,
    validate_gaze_in_wild_first_party_resolution_response,
    write_gaze_in_wild_first_party_resolution_request,
    write_gaze_in_wild_first_party_resolution_response,
)

_DEFAULT_DISTRIBUTION_EVIDENCE = Path(
    "validation/evidence/gaze-in-wild/"
    "gaze-in-wild-distribution-availability-evidence-v1.json"
)
_DEFAULT_CURRENT_LISTING_EVIDENCE = Path(
    "validation/evidence/gaze-in-wild/"
    "gaze-in-wild-current-first-party-listing-evidence-v1.json"
)


def _add_parent_evidence(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--distribution-evidence",
        type=Path,
        default=_DEFAULT_DISTRIBUTION_EVIDENCE,
        help="Reviewed historical distribution-availability evidence JSON.",
    )
    parser.add_argument(
        "--current-listing-evidence",
        type=Path,
        default=_DEFAULT_CURRENT_LISTING_EVIDENCE,
        help="Reviewed current first-party listing evidence JSON.",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the first-party resolution CLI parser."""

    parser = argparse.ArgumentParser(
        prog="gazeforge-giw-first-party-resolution",
        description=(
            "Generate and validate a deterministic Gaze-in-the-Wild first-party clarification "
            "request, then bind privacy-safe reviewed findings to a local correspondence digest."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    request = subparsers.add_parser(
        "request",
        help="Generate the public first-party archive/rights clarification request packet.",
    )
    _add_parent_evidence(request)
    request.add_argument("--output", required=True, type=Path)
    request.add_argument("--overwrite", action="store_true")

    request_validate = subparsers.add_parser(
        "request-validate",
        help="Validate one saved request against both immutable parent evidence records.",
    )
    _add_parent_evidence(request_validate)
    request_validate.add_argument("--request", required=True, type=Path)

    scaffold = subparsers.add_parser(
        "response-scaffold",
        help=(
            "Hash a local correspondence file and create a pending structured review scaffold; "
            "the correspondence body is not serialized."
        ),
    )
    _add_parent_evidence(scaffold)
    scaffold.add_argument("--request", required=True, type=Path)
    scaffold.add_argument("--correspondence", required=True, type=Path)
    scaffold.add_argument("--output", required=True, type=Path)
    scaffold.add_argument("--overwrite", action="store_true")

    response_validate = subparsers.add_parser(
        "response-validate",
        help=(
            "Validate edited structured findings against the exact request and the original local "
            "correspondence digest."
        ),
    )
    _add_parent_evidence(response_validate)
    response_validate.add_argument("--request", required=True, type=Path)
    response_validate.add_argument("--response", required=True, type=Path)
    response_validate.add_argument("--correspondence", required=True, type=Path)
    return parser


def _validated_request(args: argparse.Namespace):
    return validate_gaze_in_wild_first_party_resolution_request(
        args.request,
        args.distribution_evidence,
        args.current_listing_evidence,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run one privacy-safe first-party resolution operation and emit JSON."""

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "request":
        record = build_gaze_in_wild_first_party_resolution_request(
            args.distribution_evidence,
            args.current_listing_evidence,
        )
        write_gaze_in_wild_first_party_resolution_request(
            record,
            args.output,
            overwrite=args.overwrite,
        )
        result = {
            "record_type": record["record_type"],
            "request_fingerprint_sha256": record["request_fingerprint_sha256"],
            "output": str(args.output),
        }
    elif args.command == "request-validate":
        request = _validated_request(args)
        result = asdict(request)
        result["path"] = None if request.path is None else str(request.path)
    elif args.command == "response-scaffold":
        request = _validated_request(args)
        record = build_gaze_in_wild_first_party_resolution_response_scaffold(
            args.correspondence,
            request,
        )
        write_gaze_in_wild_first_party_resolution_response(
            record,
            args.output,
            overwrite=args.overwrite,
        )
        result = {
            "record_type": record["record_type"],
            "response_fingerprint_sha256": record["response_fingerprint_sha256"],
            "correspondence_sha256": record["correspondence_sha256"],
            "raw_correspondence_serialized": False,
            "output": str(args.output),
        }
    elif args.command == "response-validate":
        request = _validated_request(args)
        response = validate_gaze_in_wild_first_party_resolution_response(
            args.response,
            args.correspondence,
            request,
        )
        result = asdict(response)
        result["path"] = None if response.path is None else str(response.path)
    else:  # pragma: no cover - argparse guarantees a known command
        parser.error(f"Unsupported command: {args.command}")

    print(json.dumps(result, sort_keys=True, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
