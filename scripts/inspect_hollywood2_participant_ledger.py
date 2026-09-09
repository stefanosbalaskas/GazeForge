#!/usr/bin/env python3
"""Inspect an authorized local Hollywood-2 archive without extracting gaze data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from gazeforge.hollywood2_participant_ledger_intake import (
    inspect_original_archive,
    validate_intake_record,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", type=Path, default=Path("hollywood2-ledger-intake.json"))
    parser.add_argument(
        "--confirm-authorized-local-copy",
        action="store_true",
        help=(
            "Affirm that this local archive copy was obtained under terms that authorize "
            "the caller to inspect it. This does not grant redistribution rights."
        ),
    )
    args = parser.parse_args()

    record = inspect_original_archive(
        args.archive,
        authorized_local_copy=args.confirm_authorized_local_copy,
    )
    validate_intake_record(record)
    args.output.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "archive_sha256": record["archive"]["sha256"],
        "metadata_candidates": record["metadata_inspection"]["candidate_count"],
        "metadata_inspected": record["metadata_inspection"]["inspected_count"],
        "participant_identity_mapping_verified": record["mapping_boundary"][
            "participant_identity_mapping_verified"
        ],
        "record_fingerprint_sha256": record["record_fingerprint_sha256"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
