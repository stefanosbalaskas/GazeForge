"""JSON-only CLI for validating conservative VISUS source-resolution checkpoints."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from .visus_source_resolution import validate_visus_source_resolution_record


def build_parser() -> argparse.ArgumentParser:
    """Build the source-resolution checkpoint parser."""
    parser = argparse.ArgumentParser(
        prog="gazeforge-visus-source-resolution",
        description=(
            "Validate a VISUS source-resolution status checkpoint without treating it as a "
            "source audit or empirical evidence."
        ),
    )
    parser.add_argument("path", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Validate one checkpoint and emit a JSON summary."""
    args = build_parser().parse_args(argv)
    summary = validate_visus_source_resolution_record(args.path)
    print(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
