#!/usr/bin/env python3
"""Create and bind a metadata-only Gaze-in-the-Wild POR source probe."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from gazeforge.gaze_in_wild_coordinate_evidence import (
    build_first_party_por_live_probe,
    validate_gaze_in_wild_por_coordinate_evidence,
    validate_live_por_probe_against_evidence,
)

DEFAULT_EVIDENCE = Path(
    "validation/evidence/gaze-in-wild/"
    "gaze-in-wild-por-coordinate-semantics-evidence-v1.json"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    args = parser.parse_args()

    source_text = args.source.read_text(encoding="utf-8")
    probe = build_first_party_por_live_probe(source_text)
    evidence = validate_gaze_in_wild_por_coordinate_evidence(args.evidence)
    validate_live_por_probe_against_evidence(probe, args.evidence)

    args.output.write_text(
        json.dumps(probe, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("GIW POR evidence fingerprint:", evidence["evidence_fingerprint_sha256"])
    print("live probe fingerprint:", probe["probe_fingerprint_sha256"])
    print(
        "ProcessData POR coordinate space:",
        evidence["verification"]["processdata_por_coordinate_space"],
    )
    print(
        "participant mapping verified:",
        evidence["mapping_boundary"]["participant_identity_mapping_verified"],
    )
    print(
        "analysis use permitted:",
        evidence["rights_boundary"]["analysis_use_permitted"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
