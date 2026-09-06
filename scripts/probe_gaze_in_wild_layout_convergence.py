#!/usr/bin/env python3
"""Probe exact pinned files for Gaze-in-the-Wild layout/schema convergence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from gazeforge.gaze_in_wild_layout_convergence import (
    build_gaze_in_wild_layout_convergence_probe,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first-party-plot-labels", type=Path, required=True)
    parser.add_argument("--first-party-gitignore", type=Path, required=True)
    parser.add_argument("--dfki-giw", type=Path, required=True)
    parser.add_argument("--ace-giw", type=Path, required=True)
    parser.add_argument("--leo-preprocessing", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    record = build_gaze_in_wild_layout_convergence_probe(
        first_party_plot_labels=args.first_party_plot_labels.read_bytes(),
        first_party_gitignore=args.first_party_gitignore.read_bytes(),
        dfki_giw=args.dfki_giw.read_bytes(),
        ace_giw=args.ace_giw.read_bytes(),
        leo_preprocessing=args.leo_preprocessing.read_bytes(),
    )
    args.output.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(record, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
