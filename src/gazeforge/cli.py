"""Command-line entry point."""

from __future__ import annotations

import argparse
import json
from importlib.metadata import version


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gazeforge", description="Auditable AI for eye tracking.")
    parser.add_argument("--version", action="store_true", help="Print installed GazeForge version.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.version:
        print(version("gazeforge"))
    else:
        print(json.dumps({"package": "gazeforge", "status": "ready"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
