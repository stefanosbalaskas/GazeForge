"""JSON-only CLI for exact non-empirical candidate source inventories and review scaffolds."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from .source_candidate import (
    build_candidate_source_inventory,
    validate_candidate_source_inventory,
    write_candidate_source_inventory,
)
from .source_candidate_review import (
    build_candidate_source_review_scaffold,
    validate_candidate_source_review_scaffold,
    write_candidate_source_review_scaffold,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the candidate source inventory/review parser."""
    parser = argparse.ArgumentParser(
        prog="gazeforge-source-candidate",
        description=(
            "Build or revalidate exact non-empirical local inventories and manual-review "
            "scaffolds for candidate Hollywood2EM or Gaze-in-the-Wild source copies."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="Fingerprint one complete candidate source tree.")
    build.add_argument(
        "--dataset",
        required=True,
        choices=("gaze-in-the-wild", "hollywood2em"),
        help="Reviewed benchmark identity for the candidate tree.",
    )
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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run one candidate inventory/review operation and emit validated JSON."""
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
    else:
        result = validate_candidate_source_review_scaffold(
            args.review,
            args.inventory,
            args.root,
        )

    print(json.dumps(result.to_dict(), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
