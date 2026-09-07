"""Run the metadata-only Hollywood2EM ARFF-header probe."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from gazeforge.hollywood2_coordinate_metadata import (
    DEFAULT_COMMIT_SHA1,
    DEFAULT_REPOSITORY,
    build_hollywood2_coordinate_metadata_probe,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY)
    parser.add_argument("--commit-sha1", default=DEFAULT_COMMIT_SHA1)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    record = build_hollywood2_coordinate_metadata_probe(
        args.source_root,
        repository=args.repository,
        commit_sha1=args.commit_sha1,
    )
    output = Path(args.output)
    output.write_text(
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    inventory = record["header_inventory"]
    boundary = record["coordinate_boundary"]
    print("ARFF file count:", inventory["arff_file_count"])
    print("required schema count:", inventory["required_gaze_schema_file_count"])
    print(
        "author metadata complete count:",
        inventory["author_convention_metadata_complete_file_count"],
    )
    print("metadata key counts:", inventory["metadata_key_file_counts"])
    print("metadata signatures:", inventory["metadata_signatures"])
    print("header marker counts:", inventory["marker_file_counts"])
    print(
        "all headers match author metadata convention:",
        boundary["all_headers_match_author_input_metadata_convention"],
    )
    print("coordinate unit candidate:", boundary["coordinate_unit_candidate"])
    print("coordinate unit verified:", boundary["coordinate_unit_verified"])
    print("probe fingerprint:", record["probe_fingerprint_sha256"])


if __name__ == "__main__":
    main()
