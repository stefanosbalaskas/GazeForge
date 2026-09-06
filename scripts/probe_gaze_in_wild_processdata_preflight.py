#!/usr/bin/env python
"""Probe the pinned first-party GIW preprocessing bundle for ProcessData compatibility."""

from __future__ import annotations

import argparse
import json
import tempfile
import zipfile
from pathlib import Path

from gazeforge.gaze_in_wild_processdata_preflight import (
    build_gaze_in_wild_processdata_preflight_record,
    preflight_gaze_in_wild_processdata,
)
from gazeforge.native_event import file_sha256

SOURCE_REPOSITORY = "https://github.com/RSKothari/Gaze-in-Wild"
SOURCE_REVISION = "52262d44e366a53369e10ca73c5f41daf0e8f1e5"
ARCHIVE_PATH = "DataExtraction/all_preprocessing_steps.zip"
ARCHIVE_SHA256 = "5deef95a4d847b7b21a37c5d746212549b63217bd64159bec72992d82b575956"
ARCHIVE_BYTES = 72109475
MEMBER_PATH = "exports/ProcessData.mat"
MEMBER_SHA256 = "d633bbf0a3a9224b71e286ada10a63abe7761264eec7e8c25c94fcf0bbbafc63"
MEMBER_BYTES = 40528499
PARENT_EVIDENCE_FINGERPRINT = (
    "f144f5b7edcdbd02e85b53e751812c41b6567105219fbfb63c097bcefc5c9ffc"
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("repository_root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    archive = args.repository_root / ARCHIVE_PATH
    if not archive.is_file():
        raise FileNotFoundError(archive)
    if archive.stat().st_size != ARCHIVE_BYTES:
        raise RuntimeError(
            f"archive byte mismatch: expected={ARCHIVE_BYTES}, observed={archive.stat().st_size}"
        )
    if file_sha256(archive) != ARCHIVE_SHA256:
        raise RuntimeError("archive SHA-256 mismatch")

    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        if MEMBER_PATH not in names:
            raise RuntimeError(f"missing archive member {MEMBER_PATH!r}")
        if any(name.lower().endswith("labeldata.mat") for name in names):
            raise RuntimeError("unexpected LabelData member surfaced in pinned preprocessing archive")
        info = zf.getinfo(MEMBER_PATH)
        if info.file_size != MEMBER_BYTES:
            raise RuntimeError(
                f"member byte mismatch: expected={MEMBER_BYTES}, observed={info.file_size}"
            )
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "ProcessData.mat"
            with zf.open(MEMBER_PATH) as source, destination.open("wb") as target:
                while chunk := source.read(1024 * 1024):
                    target.write(chunk)
            preflight = preflight_gaze_in_wild_processdata(
                destination,
                expected_sha256=MEMBER_SHA256,
                expected_bytes=MEMBER_BYTES,
            )

    record = build_gaze_in_wild_processdata_preflight_record(
        preflight,
        source_repository=SOURCE_REPOSITORY,
        source_revision=SOURCE_REVISION,
        archive_path=ARCHIVE_PATH,
        archive_sha256=ARCHIVE_SHA256,
        member_path=MEMBER_PATH,
        parent_evidence_fingerprint_sha256=PARENT_EVIDENCE_FINGERPRINT,
    )
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "record_fingerprint_sha256": record["record_fingerprint_sha256"],
                "participant_index": preflight.participant_index,
                "trial_index": preflight.trial_index,
                "stored_rate_hz": preflight.stored_rate_hz,
                "inferred_processed_rate_hz": preflight.inferred_processed_rate_hz,
                "timestamp_count": preflight.timestamp_count,
                "timestamp_start_s": preflight.timestamp_start_s,
                "timestamp_end_s": preflight.timestamp_end_s,
                "por_shape": preflight.por_shape,
                "confidence_shape": preflight.confidence_shape,
                "scene_resolution_px": preflight.scene_resolution_px,
                "labels_present": preflight.labels_present,
                "labels_shape": preflight.labels_shape,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
