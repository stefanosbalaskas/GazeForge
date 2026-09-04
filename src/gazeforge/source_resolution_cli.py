"""JSON-only CLI for unified benchmark source-resolution checkpoint validation."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from .source_resolution import validate_source_resolution_records
from .source_resolution_discovery import validate_source_resolution_directory
from .source_resolution_lock import validate_source_resolution_bundle_lock


def build_parser() -> argparse.ArgumentParser:
    """Build the unified source-resolution validation parser."""
    parser = argparse.ArgumentParser(
        prog="gazeforge-source-resolution",
        description=(
            "Validate non-empirical benchmark source-resolution checkpoints and emit a "
            "deterministic JSON validation bundle."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Explicit source-resolution-status-v1 JSON checkpoints.",
    )
    parser.add_argument(
        "--directory",
        type=Path,
        help=(
            "Discover every *-source-resolution-*.json checkpoint in one protocol directory. "
            "Cannot be combined with explicit paths."
        ),
    )
    parser.add_argument(
        "--lock",
        type=Path,
        help=(
            "Validate the discovered directory against one reviewed "
            "source-resolution-bundle-lock-v1 JSON snapshot. Requires --directory."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Validate checkpoints and emit one JSON-only validation result."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.directory is not None and args.paths:
        parser.error("--directory cannot be combined with explicit checkpoint paths")
    if args.directory is None and not args.paths:
        parser.error("provide checkpoint paths or --directory")
    if args.lock is not None and args.directory is None:
        parser.error("--lock requires --directory")

    if args.directory is not None and args.lock is not None:
        summary = {
            "validation_bundle": validate_source_resolution_directory(args.directory),
            "bundle_lock": validate_source_resolution_bundle_lock(args.lock, args.directory),
        }
    elif args.directory is not None:
        summary = validate_source_resolution_directory(args.directory)
    else:
        summary = validate_source_resolution_records(args.paths)
    print(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
