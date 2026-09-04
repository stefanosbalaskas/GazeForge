"""JSON-only CLI for unified benchmark source-resolution checkpoint validation."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from .source_resolution import validate_source_resolution_records


def build_parser() -> argparse.ArgumentParser:
    """Build the unified source-resolution validation parser."""
    parser = argparse.ArgumentParser(
        prog="gazeforge-source-resolution",
        description=(
            "Validate one or more non-empirical benchmark source-resolution checkpoints and "
            "emit a deterministic JSON validation bundle."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="One or more source-resolution-status-v1 JSON checkpoints.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Validate checkpoints and emit one JSON-only bundle."""
    args = build_parser().parse_args(argv)
    summary = validate_source_resolution_records(args.paths)
    print(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
