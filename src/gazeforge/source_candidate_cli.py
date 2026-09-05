"""JSON-only CLI for candidate source intake, review, authorization, and lineage."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from .exceptions import BenchmarkIntegrityError
from .gaze_in_wild_audit import (
    GazeInWildSourceAuditSpec,
    load_gaze_in_wild_source_audit_spec,
)
from .gaze_in_wild_quarantine_exit import (
    build_gaze_in_wild_quarantine_exit_authorization,
    load_gaze_in_wild_quarantine_exit_authorization,
    validate_gaze_in_wild_quarantine_exit_authorization,
    write_gaze_in_wild_quarantine_exit_authorization,
)
from .hollywood2_audit import load_hollywood2_source_audit_spec
from .source_audit_lineage import (
    build_source_audit_lineage_receipt,
    write_source_audit_lineage_receipt,
)
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


def _load_json_object(path: Path, *, label: str) -> Mapping[str, object]:
    if not path.is_file():
        raise FileNotFoundError(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(f"{label} must be valid UTF-8 JSON.") from exc
    if not isinstance(payload, Mapping):
        raise BenchmarkIntegrityError(f"{label} must contain one JSON object.")
    return payload


def _require_giw_template(path: Path) -> GazeInWildSourceAuditSpec:
    spec = load_gaze_in_wild_source_audit_spec(path)
    if not isinstance(spec, GazeInWildSourceAuditSpec):
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild quarantine exit requires a GazeInWildSourceAuditSpec."
        )
    return spec


def _require_giw_apply_inputs(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    missing = [
        name
        for name in ("quarantine_exit", "recovery_review", "inventory")
        if getattr(args, name, None) is None
    ]
    if missing:
        flags = ", ".join(f"--{name.replace('_', '-')}" for name in missing)
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild authorization application requires the complete recovery "
            f"quarantine lineage: {flags}."
        )
    return args.quarantine_exit, args.recovery_review, args.inventory


def build_parser() -> argparse.ArgumentParser:
    """Build the candidate source intake/review/authorization/lineage parser."""
    parser = argparse.ArgumentParser(
        prog="gazeforge-source-candidate",
        description=(
            "Fingerprint candidate benchmark copies, scaffold manual scientific review, compile "
            "audit templates, apply separate human authorization, and verify source-audit lineage."
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

    quarantine_exit = subparsers.add_parser(
        "quarantine-exit",
        help=(
            "Create a pending Gaze-in-the-Wild recovery-quarantine exit record bound to the "
            "exact recovery review, candidate inventory, and audit template."
        ),
    )
    quarantine_exit.add_argument(
        "--recovery-review",
        required=True,
        type=Path,
        help="Saved Gaze-in-the-Wild recovery-candidate review JSON.",
    )
    quarantine_exit.add_argument(
        "--inventory",
        required=True,
        type=Path,
        help="Saved exact generic candidate inventory JSON.",
    )
    quarantine_exit.add_argument(
        "--template",
        required=True,
        type=Path,
        help="Saved non-empirical Gaze-in-the-Wild audit-template JSON.",
    )
    quarantine_exit.add_argument(
        "--root", required=True, type=Path, help="Candidate source directory."
    )
    quarantine_exit.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Quarantine-exit JSON path outside the candidate source directory.",
    )
    quarantine_exit.add_argument(
        "--overwrite", action="store_true", help="Replace an existing output file."
    )

    quarantine_exit_validate = subparsers.add_parser(
        "quarantine-exit-validate",
        help=(
            "Validate an edited Gaze-in-the-Wild quarantine-exit decision against the exact "
            "candidate tree, recovery review, inventory, and audit template."
        ),
    )
    quarantine_exit_validate.add_argument(
        "--quarantine-exit",
        required=True,
        type=Path,
        help="Edited quarantine-exit decision JSON.",
    )
    quarantine_exit_validate.add_argument(
        "--recovery-review",
        required=True,
        type=Path,
        help="Saved Gaze-in-the-Wild recovery-candidate review JSON.",
    )
    quarantine_exit_validate.add_argument(
        "--inventory",
        required=True,
        type=Path,
        help="Saved exact generic candidate inventory JSON.",
    )
    quarantine_exit_validate.add_argument(
        "--template",
        required=True,
        type=Path,
        help="Saved non-empirical Gaze-in-the-Wild audit-template JSON.",
    )
    quarantine_exit_validate.add_argument(
        "--root", required=True, type=Path, help="Candidate source directory."
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
            "does not execute the source audit. Recovered Gaze-in-the-Wild candidates also require "
            "their exact quarantine-exit lineage."
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
        "--quarantine-exit",
        type=Path,
        help="Authorized Gaze-in-the-Wild recovery-quarantine exit JSON.",
    )
    authorization_apply.add_argument(
        "--recovery-review",
        type=Path,
        help="Gaze-in-the-Wild recovery-candidate review JSON used by the exit decision.",
    )
    authorization_apply.add_argument(
        "--inventory",
        type=Path,
        help="Exact generic candidate inventory JSON used by the exit decision.",
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

    lineage = subparsers.add_parser(
        "lineage",
        help=(
            "Verify an audit report against the exact reviewed template and authorization, then "
            "write a fingerprinted lineage receipt."
        ),
    )
    _add_dataset_argument(lineage)
    lineage.add_argument(
        "--template", required=True, type=Path, help="Original non-empirical audit-template JSON."
    )
    lineage.add_argument(
        "--authorization", required=True, type=Path, help="Authorized decision JSON."
    )
    lineage.add_argument(
        "--audit-report", required=True, type=Path, help="Verified source-audit report JSON."
    )
    lineage.add_argument("--root", required=True, type=Path, help="Candidate source directory.")
    lineage.add_argument(
        "--quarantine-exit",
        type=Path,
        help="Authorized Gaze-in-the-Wild recovery-quarantine exit JSON.",
    )
    lineage.add_argument(
        "--recovery-review",
        type=Path,
        help="Gaze-in-the-Wild recovery-candidate review JSON used by the exit decision.",
    )
    lineage.add_argument(
        "--inventory",
        type=Path,
        help="Exact generic candidate inventory JSON used by the exit decision.",
    )
    lineage.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Lineage receipt JSON path outside the candidate source directory.",
    )
    lineage.add_argument(
        "--overwrite", action="store_true", help="Replace an existing output file."
    )
    return parser


def _validated_giw_exit_for_args(
    args: argparse.Namespace,
    template: GazeInWildSourceAuditSpec,
):
    quarantine_exit_path, recovery_review, inventory_path = _require_giw_apply_inputs(args)
    inventory = validate_candidate_source_inventory(inventory_path, args.root)
    exit_record = load_gaze_in_wild_quarantine_exit_authorization(quarantine_exit_path)
    return validate_gaze_in_wild_quarantine_exit_authorization(
        exit_record,
        root=args.root,
        recovery_record_or_path=recovery_review,
        inventory=inventory,
        spec=template,
    )


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
    elif args.command == "quarantine-exit":
        inventory = validate_candidate_source_inventory(args.inventory, args.root)
        template = _require_giw_template(args.template)
        result = build_gaze_in_wild_quarantine_exit_authorization(
            args.root,
            args.recovery_review,
            inventory,
            template,
        )
        write_gaze_in_wild_quarantine_exit_authorization(
            result,
            args.output,
            candidate_root=args.root,
            overwrite=args.overwrite,
        )
    elif args.command == "quarantine-exit-validate":
        inventory = validate_candidate_source_inventory(args.inventory, args.root)
        template = _require_giw_template(args.template)
        result = validate_gaze_in_wild_quarantine_exit_authorization(
            args.quarantine_exit,
            root=args.root,
            recovery_record_or_path=args.recovery_review,
            inventory=inventory,
            spec=template,
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
    elif args.command == "authorization-apply":
        template = _load_audit_spec(args.template, args.dataset)
        authorization_record = validate_candidate_source_audit_authorization(
            args.authorization,
            template,
        )
        exit_record = None
        if args.dataset == "gaze-in-the-wild":
            assert isinstance(template, GazeInWildSourceAuditSpec)
            exit_record = _validated_giw_exit_for_args(args, template)
        elif any(
            value is not None
            for value in (args.quarantine_exit, args.recovery_review, args.inventory)
        ):
            raise BenchmarkIntegrityError(
                "Gaze-in-the-Wild recovery-lineage arguments cannot be used for Hollywood2EM."
            )
        result = authorize_candidate_source_audit_template(
            template,
            authorization_record,
            gaze_in_wild_quarantine_exit=exit_record,
        )
        write_authorized_source_audit_spec(
            result,
            args.output,
            candidate_root=args.root,
            overwrite=args.overwrite,
        )
    else:
        template = _load_audit_spec(args.template, args.dataset)
        authorization_record = validate_candidate_source_audit_authorization(
            args.authorization,
            template,
        )
        exit_record = None
        if args.dataset == "gaze-in-the-wild":
            assert isinstance(template, GazeInWildSourceAuditSpec)
            exit_record = _validated_giw_exit_for_args(args, template)
        elif any(
            value is not None
            for value in (args.quarantine_exit, args.recovery_review, args.inventory)
        ):
            raise BenchmarkIntegrityError(
                "Gaze-in-the-Wild recovery-lineage arguments cannot be used for Hollywood2EM."
            )
        audit_report = _load_json_object(args.audit_report, label="Source-audit report")
        result = build_source_audit_lineage_receipt(
            template,
            authorization_record,
            audit_report,
            gaze_in_wild_quarantine_exit=exit_record,
        )
        write_source_audit_lineage_receipt(
            result,
            args.output,
            candidate_root=args.root,
            overwrite=args.overwrite,
        )

    print(json.dumps(result.to_dict(), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
