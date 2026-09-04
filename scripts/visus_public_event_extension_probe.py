from __future__ import annotations

import csv
import hashlib
import json
import statistics
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

UPSTREAM_REPO = "Maurice189/eye-slitscan"
UPSTREAM_COMMIT = "a8ea2402936122f9e5c98152460bd16a4ba97740"
ORIGINAL_VISUS_DIALOG_DURATION_SECONDS = 19.0

FILES: dict[str, dict[str, Any]] = {
    "P5B": {
        "path": "core/importer/eye-tracker-output/test/Tobii_exports/01-OK.tsv",
        "bytes": 263072,
        "git_blob_sha1": "fd2371fd6f44de8a188e52439a0fea6b2054f975",
    },
    "P3A": {
        "path": "core/importer/eye-tracker-output/test/Tobii_exports/02-OK.tsv",
        "bytes": 256538,
        "git_blob_sha1": "e39b0c0d2c50c22dec76b93581a4ca2bce784546",
    },
    "lock_P2B_dialog": {
        "path": "core/importer/eye-tracker-output/test/Tobii_exports/.~lock.P2B-03-dialog.tsv#",
        "bytes": 86,
        "git_blob_sha1": "512f8242f20b8ecef29fcd45703e157f67d826c6",
    },
    "lock_P4B_dialog": {
        "path": "core/importer/eye-tracker-output/test/Tobii_exports/.~lock.P4B-03-dialog.tsv#",
        "bytes": 86,
        "git_blob_sha1": "4ccb75c30a65dea74aa221f1082c3f0a789b2515",
    },
    "lock_P6A_dialog": {
        "path": "core/importer/eye-tracker-output/test/Tobii_exports/.~lock.P6A-03-dialog.tsv#",
        "bytes": 86,
        "git_blob_sha1": "03bedf17e307276eb8d9aad5f7f8070f8121f9c5",
    },
}

PARTICIPANT_KEYS = ("P5B", "P3A")
LOCK_KEYS = ("lock_P2B_dialog", "lock_P4B_dialog", "lock_P6A_dialog")


def _raw_url(path: str) -> str:
    quoted = urllib.parse.quote(path, safe="/")
    return f"https://raw.githubusercontent.com/{UPSTREAM_REPO}/{UPSTREAM_COMMIT}/{quoted}"


def _git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


def _fetch_exact(key: str, root: Path) -> tuple[Path, dict[str, Any]]:
    spec = FILES[key]
    url = _raw_url(spec["path"])
    request = urllib.request.Request(url, headers={"User-Agent": "GazeForge-VISUS-event-probe/1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read()
    observed_git = _git_blob_sha1(data)
    if observed_git != spec["git_blob_sha1"]:
        raise RuntimeError(
            f"Git blob mismatch for {key}: expected {spec['git_blob_sha1']}, got {observed_git}"
        )
    if len(data) != spec["bytes"]:
        raise RuntimeError(
            f"Byte-size mismatch for {key}: expected {spec['bytes']}, got {len(data)}"
        )
    target = root / key
    target.write_bytes(data)
    return target, {
        "path": spec["path"],
        "url": url,
        "bytes": len(data),
        "git_blob_sha1": observed_git,
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _to_int(value: str) -> int | None:
    value = value.strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        try:
            return int(float(value.replace(",", ".")))
        except ValueError:
            return None


def _metadata(lines: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in lines:
        if line.startswith("Timestamp\t"):
            break
        if "\t" not in line:
            continue
        key, value = line.split("\t", 1)
        key = key.strip().rstrip(":")
        value = value.strip()
        if key and value:
            result[key] = value
    return result


def _parse_export(path: Path, expected_participant: str) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    metadata = _metadata(lines)
    if metadata.get("Recording name") != expected_participant:
        raise RuntimeError(
            f"Unexpected recording name for {expected_participant}: {metadata.get('Recording name')}"
        )
    if metadata.get("Participant") != expected_participant:
        raise RuntimeError(
            f"Unexpected participant for {expected_participant}: {metadata.get('Participant')}"
        )
    if metadata.get("Recording resolution") != "1920 x 1200":
        raise RuntimeError(
            f"Unexpected recording resolution for {expected_participant}: "
            f"{metadata.get('Recording resolution')}"
        )

    header_index = next(i for i, line in enumerate(lines) if line.startswith("Timestamp\t"))
    reader = csv.DictReader(lines[header_index:], delimiter="\t")
    rows = list(reader)
    if not rows:
        raise RuntimeError(f"No TSV rows in {path}")

    movie_start = [row for row in rows if row.get("Event") == "MovieStart"]
    movie_end = [row for row in rows if row.get("Event") == "MovieEnd"]
    if len(movie_start) != 1 or len(movie_end) != 1:
        raise RuntimeError(
            f"Expected one MovieStart/MovieEnd for {expected_participant}, got "
            f"{len(movie_start)}/{len(movie_end)}"
        )
    start_ms = _to_int(movie_start[0].get("Timestamp", ""))
    end_ms = _to_int(movie_end[0].get("Timestamp", ""))
    if start_ms is None or end_ms is None or end_ms <= start_ms:
        raise RuntimeError(f"Invalid movie boundary for {expected_participant}")

    samples = [row for row in rows if _to_int(row.get("MicroSecondTimestamp", "")) is not None]
    if not samples:
        raise RuntimeError(f"No sample rows in {path}")

    media_geometry = sorted(
        {
            (_to_int(row.get("MediaWidth", "")), _to_int(row.get("MediaHeight", "")))
            for row in samples
            if _to_int(row.get("MediaWidth", "")) is not None
            and _to_int(row.get("MediaHeight", "")) is not None
        }
    )
    if media_geometry != [(1920, 1080)]:
        raise RuntimeError(f"Unexpected media geometry for {expected_participant}: {media_geometry}")

    microseconds = [_to_int(row.get("MicroSecondTimestamp", "")) for row in samples]
    microseconds = [value for value in microseconds if value is not None]
    positive_deltas = [b - a for a, b in zip(microseconds, microseconds[1:]) if b > a]
    if not positive_deltas:
        raise RuntimeError(f"No positive sample intervals for {expected_participant}")
    median_delta_us = statistics.median(positive_deltas)
    inferred_hz = 1_000_000.0 / median_delta_us
    if not 59.0 <= inferred_hz <= 61.0:
        raise RuntimeError(
            f"Unexpected sampling rate for {expected_participant}: {inferred_hz} Hz"
        )

    both_eye_valid = sum(
        1
        for row in samples
        if _to_int(row.get("ValidityLeft", "")) == 0
        and _to_int(row.get("ValidityRight", "")) == 0
    )

    fixation_events: list[dict[str, int]] = []
    previous_index: int | None = None
    for row in samples:
        index = _to_int(row.get("FixationIndex", ""))
        if index is None or index <= 0:
            previous_index = None
            continue
        if index == previous_index:
            continue
        duration = _to_int(row.get("FixationDuration", "")) or 0
        x = _to_int(row.get("MappedFixationPointX", ""))
        y = _to_int(row.get("MappedFixationPointY", ""))
        fixation_events.append(
            {
                "fixation_index": index,
                "duration_ms": duration,
                "x": x if x is not None else -1,
                "y": y if y is not None else -1,
            }
        )
        previous_index = index

    total_fixation_duration = sum(event["duration_ms"] for event in fixation_events)
    in_media_fixations = sum(
        1
        for event in fixation_events
        if 0 <= event["x"] < 1920 and 0 <= event["y"] < 1080
    )
    first_sample_ts = _to_int(samples[0].get("Timestamp", ""))
    last_sample_ts = _to_int(samples[-1].get("Timestamp", ""))

    return {
        "participant": expected_participant,
        "recording_name": metadata["Recording name"],
        "recording_resolution": metadata["Recording resolution"],
        "eye": metadata.get("Eye"),
        "validity_filter": metadata.get("Validity"),
        "fixation_filter": metadata.get("Fixation filter"),
        "velocity_threshold": _to_int(metadata.get("Velocity threshold", "")),
        "distance_threshold": _to_int(metadata.get("Distance threshold", "")),
        "movie_start_timestamp_ms": start_ms,
        "movie_end_timestamp_ms": end_ms,
        "movie_span_ms": end_ms - start_ms,
        "movie_span_seconds": (end_ms - start_ms) / 1000.0,
        "first_sample_timestamp_ms": first_sample_ts,
        "last_sample_timestamp_ms": last_sample_ts,
        "sample_count": len(samples),
        "media_geometry": [list(item) for item in media_geometry],
        "valid_both_eye_samples": both_eye_valid,
        "valid_both_eye_fraction": both_eye_valid / len(samples),
        "median_positive_sample_delta_us": median_delta_us,
        "inferred_sampling_rate_hz": inferred_hz,
        "fixation_event_count": len(fixation_events),
        "total_fixation_duration_ms": total_fixation_duration,
        "fixations_with_on_screen_mapped_point": in_media_fixations,
        "on_screen_fixation_fraction": (
            in_media_fixations / len(fixation_events) if fixation_events else 0.0
        ),
    }


def _parse_lock(path: Path, key: str) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig").strip()
    parts = text.split(",")
    if len(parts) < 5:
        raise RuntimeError(f"Unexpected LibreOffice lock format for {key}: {text!r}")
    return {
        "ledger_key": key,
        "content": text,
        "author": parts[0],
        "user": parts[1],
        "host": parts[2],
        "timestamp": parts[3],
        "profile_uri": parts[4].rstrip(";"),
        "empirical_data": False,
        "provenance_only": True,
    }


def main() -> None:
    root = Path(".visus-public-event-extension-probe")
    root.mkdir(exist_ok=True)

    source_files: dict[str, Any] = {}
    local_paths: dict[str, Path] = {}
    for key in FILES:
        local_paths[key], source_files[key] = _fetch_exact(key, root)

    participants = [_parse_export(local_paths[key], key) for key in PARTICIPANT_KEYS]
    locks = [_parse_lock(local_paths[key], key) for key in LOCK_KEYS]

    durations = [row["movie_span_seconds"] for row in participants]
    dialog_duration_match = all(
        abs(value - ORIGINAL_VISUS_DIALOG_DURATION_SECONDS) <= 0.1 for value in durations
    )
    if not dialog_duration_match:
        raise RuntimeError(f"The two complete segments no longer match the 19 s VISUS dialog: {durations}")

    aggregate = {
        "participant_count": len(participants),
        "sample_count": sum(row["sample_count"] for row in participants),
        "valid_both_eye_samples": sum(row["valid_both_eye_samples"] for row in participants),
        "fixation_event_count": sum(row["fixation_event_count"] for row in participants),
        "total_fixation_duration_ms": sum(row["total_fixation_duration_ms"] for row in participants),
        "fixations_with_on_screen_mapped_point": sum(
            row["fixations_with_on_screen_mapped_point"] for row in participants
        ),
    }
    aggregate["valid_both_eye_fraction"] = (
        aggregate["valid_both_eye_samples"] / aggregate["sample_count"]
    )
    aggregate["on_screen_fixation_fraction"] = (
        aggregate["fixations_with_on_screen_mapped_point"]
        / aggregate["fixation_event_count"]
    )

    result: dict[str, Any] = {
        "record_type": "visus-public-event-extension-probe-v1",
        "status": "probe_only",
        "upstream": {
            "repository": UPSTREAM_REPO,
            "commit": UPSTREAM_COMMIT,
            "files": source_files,
        },
        "coverage": {
            "participants": list(PARTICIPANT_KEYS),
            "participant_count": len(PARTICIPANT_KEYS),
            "complete_tobii_exports": 2,
            "provenance_lockfiles": 3,
            "full_visus_participant_count": 25,
            "full_visus_stimulus_count": 11,
            "full_visus_recovered": False,
        },
        "participants": participants,
        "aggregate": aggregate,
        "stimulus_inference": {
            "candidate": "03-dialog",
            "original_visus_duration_seconds": ORIGINAL_VISUS_DIALOG_DURATION_SECONDS,
            "observed_segment_durations_seconds": durations,
            "duration_matches_candidate": dialog_duration_match,
            "same_directory_dialog_lockfiles": [
                "P2B-03-dialog.tsv",
                "P4B-03-dialog.tsv",
                "P6A-03-dialog.tsv",
            ],
            "identity_status": "strongly-inferred-not-file-bound",
            "stimulus_identity_resolved": False,
            "aoi_annotation_recovered_for_candidate": False,
        },
        "provenance_lockfiles": locks,
        "reuse_boundary": {
            "analysis_use_basis_recorded": True,
            "analysis_use_basis": (
                "An Osnabrueck University WACV 2017 research page states that converted eye-tracking "
                "datasets, including the Kurzhals dataset, are provided for research purposes."
            ),
            "source_license_resolved": False,
            "source_bytes_redistributed_by_gazeforge": False,
            "unrestricted_redistribution_asserted": False,
        },
        "scientific_boundary": {
            "real_external_tobii_60hz_exports": True,
            "participant_identity_file_bound": True,
            "stimulus_identity_file_bound": False,
            "dialog_assignment_is_inference": True,
            "dynamic_aoi_metrics_created": False,
            "human_human_agreement_created": False,
            "model_validation_created": False,
            "native_gp3_evidence": False,
            "original_full_visus_source_resolved": False,
            "frozen_evidence_created": False,
        },
    }
    canonical = json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
    result["probe_fingerprint_sha256"] = hashlib.sha256(canonical).hexdigest()
    output = Path("visus_public_event_extension_probe.json")
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
