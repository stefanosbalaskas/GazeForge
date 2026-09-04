"""JSON-only CLI for candidate source intake, review, templates, and authorization."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from .gaze_in_wild_audit import load_gaze_in_wild_source_audit_spec
from .hollywood2_audit import load_hollywood2_source_audit_spec
from .source_candidate import (
    build_candidate_source_inventory,
    validate_candidate_source_inventory,
    write_candidate_source_inventory,
)
from .source_candidate_audit_template import (
    compile_candidate_source_audit_template,
    write_candidate_source_audit_template,
)
from .source_candidate_authorization import (
    authorize_candidate_source_audit_template,
    build_candidate_source_audit_authorization,
    validate_candidate_source_audit_authorization,
    write_authorized_source_audit_spec,
    write_candidate_source_audit_authorization,
)
from .source_candidate_review import (
    build_candidate_source_review_scaffold,
    validate_candidate_source_review_scaffold,
    write_candidate_source_review_scaffold,
)

_DATASETS = ("gaze-in-the-wild", "hollywood2em")


def _add_dataset_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--dataset",
        required=True,
        choices=_DATASETS,
        help="Reviewed benchmark identity for the candidate source copy.",
    )


def _load_audit_spec(path: Path, dataset: str):
    if dataset == "hollywood2em":
        return load_hollywood2_source_audit_spec(path)
    return load_gaze_in_wild_source_audit_spec(path)


def build_parser() -> argparse.ArgumentParser:
    """Build the candidate source intake/review/authorization parser."""
    parser = argparse.ArgumentParser(
        prog="gazeforge-source-candidate",
        description=(
            "Fingerprint candidate benchmark copies, scaffold manual scientific review, compile "
            "non-empirical audit templates, and apply separate human authorization decisions."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="Fingerprint one complete candidate source tree.")
    _add_dataset_argument(build)
    build.add_argument("--root", required=True, type=Path, help="Candidate source directory.")
    build.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Inventory JSON path outside the candidate source directory.",
    )
    build.add_argument("--overwrite", action="store_true", help="Replace an existing output file.")

    validate = subparsers.add_parser(
        "validate",
        help="Revalidate a saved candidate inventory against its complete current local tree.",
    )
    validate.add_argument("--inventory", required=True, type=Path, help="Saved inventory JSON.")
    validate.add_argument("--root", required=True, type=Path, help="Candidate source directory.")

    review = subparsers.add_parser(
        "review",
        help=(
            "Create a non-empirical manual-review scaffold bound to an already saved exact "
            "candidate inventory."
        ),
    )
    review.add_argument("--inventory", required=True, type=Path, help="Saved inventory JSON.")
    review.add_argument("--root", required=True, type=Path, help="Candidate source directory.")
    review.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Review-scaffold JSON path outside the candidate source directory.",
    )
    review.add_argument("--overwrite", action="store_true", help="Replace an existing output file.")

    review_validate = subparsers.add_parser(
        "review-validate",
        help=(
            "Revalidate an edited review scaffold against its exact saved inventory and current "
            "candidate tree."
        ),
    )
    review_validate.add_argument(
        "--review", required=True, type=Path, help="Saved review-scaffold JSON."
    )
    review_validate.add_argument(
        "--inventory", required=True, type=Path, help="Saved inventory JSON."
    )
    review_validate.add_argument(
        "--root", required=True, type=Path, help="Candidate source directory."
    )

    audit_template = subparsers.add_parser(
        "audit-template",
        help=(
            "Compile a completed candidate review into a dataset-specific audit specification "
            "that remains dataset_status='template'."
        ),
    )
    audit_template.add_argument(
        "--review", required=True, type=Path, help="Completed review-scaffold JSON."
    )
    audit_template.add_argument(
        "--inventory", required=True, type=Path, help="Saved exact candidate inventory JSON."
    )
    audit_template.add_argument(
        "--root", required=True, type=Path, help="Candidate source directory."
    )
    audit_template.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Dataset-specific audit-template JSON outside the candidate source directory.",
    )
    audit_template.add_argument(
        "--overwrite", action="store_true", help="Replace an existing output file."
    )

    authorization = subparsers.add_parser(
        "authorization",
        help="Create a pending human authorization record bound to one exact audit template.",
    )
    _add_dataset_argument(authorization)
    authorization.add_argument(
        "--template", required=True, type=Path, help="Saved non-empirical audit-template JSON."
    )
    authorization.add_argument(
        "--root", required=True, type=Path, help="Candidate source directory."
    )
    authorization.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Authorization JSON path outside the candidate source directory.",
    )
    authorization.add_argument(
        "--overwrite", action="store_true", help="Replace an existing output file."
    )

    authorization_validate = subparsers.add_parser(
        "authorization-validate",
        help="Validate a manual authorization decision against the exact audit template.",
    )
    _add_dataset_argument(authorization_validate)
    authorization_validate.add_argument(
        "--template", required=True, type=Path, help="Saved non-empirical audit-template JSON."
    )
    authorization_validate.add_argument(
        "--authorization", required=True, type=Path, help="Edited authorization JSON."
    )

    authorization_apply = subparsers.add_parser(
        "authorization-apply",
        help=(
            "Apply an explicit authorized decision to materialize an empirical audit spec; this "
            "does not execute the source audit."
        ),
    )
    _add_dataset_argument(authorization_apply)
    authorization_apply.add_argument(
        "--template", required=True, type=Path, help="Saved non-empirical audit-template JSON."
    )
    authorization_apply.add_argument(
        "--authorization", required=True, type=Path, help="Authorized decision JSON."
    )
    authorization_apply.add_argument(
        "--root", required=True, type=Path, help="Candidate source directory."
    )
    authorization_apply.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Authorized empirical audit-spec JSON outside the candidate source directory.",
    )
    authorization_apply.add_argument(
        "--overwrite", action="store_true", help="Replace an existing output file."
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run one candidate source operation and emit deterministic JSON."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "build":
        result = build_candidate_source_inventory(args.root, dataset_key=args.dataset)
        write_candidate_source_inventory(result, args.output, overwrite=args.overwrite)
    elif args.command == "validate":
        result = validate_candidate_source_inventory(args.inventory, args.root)
    elif args.command == "review":
        inventory = validate_candidate_source_inventory(args.inventory, args.root)
        result = build_candidate_source_review_scaffold(inventory)
        write_candidate_source_review_scaffold(result, args.output, overwrite=args.overwrite)
    elif args.command == "review-validate":
        result = validate_candidate_source_review_scaffold(
            args.review,
            args.inventory,
            args.root,
        )
    elif args.command == "audit-template":
        scaffold = validate_candidate_source_review_scaffold(
            args.review,
            args.inventory,
            args.root,
        )
        result = compile_candidate_source_audit_template(scaffold)
        write_candidate_source_audit_template(
            result,
            args.output,
            candidate_root=args.root,
            overwrite=args.overwrite,
        )
    elif args.command == "authorization":
        template = _load_audit_spec(args.template, args.dataset)
        result = build_candidate_source_audit_authorization(template)
        write_candidate_source_audit_authorization(
            result,
            args.output,
            candidate_root=args.root,
            overwrite=args.overwrite,
        )
    elif args.command == "authorization-validate":
        template = _load_audit_spec(args.template, args.dataset)
        result = validate_candidate_source_audit_authorization(
            args.authorization,
            template,
        )
    else:
        template = _load_audit_spec(args.template, args.dataset)
        authorization_record = validate_candidate_source_audit_authorization(
            args.authorization,
            template,
        )
        result = authorize_candidate_source_audit_template(template, authorization_record)
        write_authorized_source_audit_spec(
            result,
            args.output,
            candidate_root=args.root,
            overwrite=args.overwrite,
        )

    print(json.dumps(result.to_dict(), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
