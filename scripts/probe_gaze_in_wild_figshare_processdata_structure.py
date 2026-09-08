#!/usr/bin/env python
"""Probe exact original Gaze-in-the-Wild ProcessData structure and timestamp grids.

This probe is deliberately structural/provenance-only. It streams each of the
68 original-publication ProcessData files from the official Figshare deposit,
verifies frozen Figshare size/MD5 plus a previously reviewed SHA-256 identity,
loads each ProcessData object, records adapter-relevant structure, and deletes
the raw MAT file immediately.

The summary may establish exact-file structural coverage, processed timestamp-
grid rate distribution, and ProcessData/LabelData recording-token pairing. It
does not establish task names, acquisition hardware cadence, model validity,
GP3 validity, or quarantine exit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import tempfile
import time
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

from gazeforge.gaze_in_wild_processdata_preflight import (
    preflight_gaze_in_wild_processdata,
)

PROCESS_LABEL = "ProcessData"
LABEL_LABEL = "LabelData"
EXCLUDED_LABEL = "ProcessData_cleaned"
USER_AGENT = "GazeForgeGIWProcessDataStructureProbe/1.0"
CHUNK_SIZE = 4 * 1024 * 1024
PROCESS_NAME_RE = re.compile(r"^PrIdx_(\d+)_TrIdx_(\d+)\.mat$")
LABEL_NAME_RE = re.compile(r"^PrIdx_(\d+)_TrIdx_(\d+)_Lbr_(\d+)\.mat$")
EXPECTED_IDENTITY_RECORD_TYPE = "gaze-in-wild-processdata-exact-sha256-ledger-v1"
EXPECTED_IDENTITY_EVIDENCE_FINGERPRINT = (
    "85f131389315a1185e3a8973629c8e5ee3417bb73704de8054366e508af0a2e2"
)
EXPECTED_SHA256_MANIFEST = (
    "162bf688fbd0bfdaf79a11d423f3689abd31bea9a4e8423bc03020ebd598354d"
)
EXPECTED_STABLE_PROCESSDATA_IDENTITY = (
    "7e48396fcfe30e2170708c9d5910caea785ceff1dd06b0455e5715a01e52d3ea"
)
EXPECTED_EXACT_BYTE_EVIDENCE = (
    "dbf277d698266fe53e337a15fc342e9af1835460d2bcc69c3992635de8fa0a00"
)


class ProcessDataStructureProbeError(RuntimeError):
    """Fail-closed structural/provenance probe error."""


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _evidence_fingerprint(record: dict[str, Any]) -> str:
    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    return _canonical_sha(body)


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProcessDataStructureProbeError(f"Could not load {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ProcessDataStructureProbeError(f"{label} must contain one JSON object.")
    return value


def _items_by_label(frozen: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items = frozen.get("items")
    if not isinstance(items, list):
        raise ProcessDataStructureProbeError("Frozen Figshare metadata items must be a list.")
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            raise ProcessDataStructureProbeError("Frozen Figshare item must be an object.")
        label = str(item.get("label"))
        if label in result:
            raise ProcessDataStructureProbeError(f"Duplicate frozen Figshare label {label!r}.")
        result[label] = item
    for label in (PROCESS_LABEL, LABEL_LABEL, EXCLUDED_LABEL):
        if label not in result:
            raise ProcessDataStructureProbeError(f"Frozen Figshare metadata lacks {label!r}.")
    return result


def _validate_identity_ledger(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    if ledger.get("record_type") != EXPECTED_IDENTITY_RECORD_TYPE:
        raise ProcessDataStructureProbeError("Unexpected ProcessData identity-ledger type.")
    if ledger.get("evidence_fingerprint_sha256") != EXPECTED_IDENTITY_EVIDENCE_FINGERPRINT:
        raise ProcessDataStructureProbeError("ProcessData identity-ledger fingerprint drifted.")
    if _evidence_fingerprint(ledger) != EXPECTED_IDENTITY_EVIDENCE_FINGERPRINT:
        raise ProcessDataStructureProbeError("ProcessData identity-ledger body drifted.")
    binding = ledger.get("source_binding")
    if not isinstance(binding, dict):
        raise ProcessDataStructureProbeError("ProcessData identity-ledger binding is missing.")
    if binding.get("figshare_project_id") != 74580:
        raise ProcessDataStructureProbeError("ProcessData Figshare project binding drifted.")
    if binding.get("figshare_article_id") != 11673645:
        raise ProcessDataStructureProbeError("ProcessData Figshare article binding drifted.")
    if (
        binding.get("reviewed_exact_byte_evidence_fingerprint_sha256")
        != EXPECTED_EXACT_BYTE_EVIDENCE
    ):
        raise ProcessDataStructureProbeError("ProcessData exact-byte evidence binding drifted.")
    if (
        binding.get("stable_processdata_identity_fingerprint_sha256")
        != EXPECTED_STABLE_PROCESSDATA_IDENTITY
    ):
        raise ProcessDataStructureProbeError("Stable ProcessData identity binding drifted.")

    files = ledger.get("files")
    if not isinstance(files, list) or len(files) != 68:
        raise ProcessDataStructureProbeError("ProcessData identity ledger must contain 68 files.")
    manifest_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in files:
        if not isinstance(row, dict):
            raise ProcessDataStructureProbeError("Malformed ProcessData identity row.")
        name = row.get("name")
        sha256 = row.get("sha256")
        if (
            not isinstance(name, str)
            or PROCESS_NAME_RE.fullmatch(name) is None
            or name in seen
        ):
            raise ProcessDataStructureProbeError("Invalid/duplicate ProcessData identity filename.")
        if (
            not isinstance(sha256, str)
            or len(sha256) != 64
            or any(char not in "0123456789abcdef" for char in sha256)
        ):
            raise ProcessDataStructureProbeError(f"Invalid ProcessData SHA-256 for {name}.")
        seen.add(name)
        manifest_rows.append({"name": name, "sha256": sha256})
    manifest = _canonical_sha(manifest_rows)
    if manifest != EXPECTED_SHA256_MANIFEST:
        raise ProcessDataStructureProbeError("ProcessData exact SHA-256 manifest drifted.")
    if ledger.get("sha256_manifest_sha256") != manifest:
        raise ProcessDataStructureProbeError("Stored ProcessData SHA-256 manifest drifted.")
    if ledger.get("file_count") != 68:
        raise ProcessDataStructureProbeError("ProcessData identity-ledger file count drifted.")
    return manifest_rows


def _frozen_md5(row: dict[str, Any]) -> str:
    supplied = row.get("supplied_md5")
    computed = row.get("computed_md5")
    if not isinstance(supplied, str) or not isinstance(computed, str):
        raise ProcessDataStructureProbeError(f"Missing frozen MD5 for {row.get('name')}.")
    if supplied.lower() != computed.lower():
        raise ProcessDataStructureProbeError(f"Frozen MD5 disagreement for {row.get('name')}.")
    return supplied.lower()


def _frozen_process_rows(item: dict[str, Any]) -> dict[str, dict[str, Any]]:
    files = item.get("files")
    if not isinstance(files, list) or len(files) != 68:
        raise ProcessDataStructureProbeError("Frozen ProcessData must contain exactly 68 files.")
    result: dict[str, dict[str, Any]] = {}
    for row in files:
        if not isinstance(row, dict):
            raise ProcessDataStructureProbeError("Malformed frozen ProcessData file row.")
        name = row.get("name")
        if not isinstance(name, str) or name in result:
            raise ProcessDataStructureProbeError("Invalid/duplicate frozen ProcessData filename.")
        result[name] = row
    return result


def _crosscheck_identity_rows(
    identity_rows: list[dict[str, Any]],
    frozen_rows: dict[str, dict[str, Any]],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    paired: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for identity in identity_rows:
        name = str(identity["name"])
        if name not in frozen_rows:
            raise ProcessDataStructureProbeError(
                f"SHA-256 ledger contains unknown ProcessData file {name!r}."
            )
        frozen = frozen_rows[name]
        file_id = frozen.get("id")
        size = frozen.get("size")
        md5 = _frozen_md5(frozen)
        if not isinstance(file_id, int) or not isinstance(size, int) or size <= 0:
            raise ProcessDataStructureProbeError(f"Invalid frozen identity for {name}.")
        if frozen.get("is_link_only") is not False:
            raise ProcessDataStructureProbeError(f"Refusing link-only ProcessData file {name}.")
        url = frozen.get("download_url")
        if not isinstance(url, str) or not url.startswith("https://"):
            raise ProcessDataStructureProbeError(f"Invalid ProcessData HTTPS URL for {name}.")
        paired.append(
            (
                {
                    "figshare_file_id": file_id,
                    "name": name,
                    "size_bytes": size,
                    "md5": md5,
                    "sha256": identity["sha256"],
                },
                frozen,
            )
        )
    if len(paired) != 68 or set(frozen_rows) != {row["name"] for row in identity_rows}:
        raise ProcessDataStructureProbeError("ProcessData SHA/frozen coverage is incomplete.")
    return paired


def _download_verified(
    identity: dict[str, Any],
    frozen: dict[str, Any],
    destination: Path,
    retries: int,
) -> int:
    expected_size = int(identity["size_bytes"])
    expected_md5 = str(identity["md5"])
    expected_sha256 = str(identity["sha256"])
    url = str(frozen["download_url"])
    name = str(identity["name"])
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        observed_size = 0
        md5 = hashlib.md5(usedforsecurity=False)
        sha256 = hashlib.sha256()
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with (
                urllib.request.urlopen(request, timeout=180) as response,
                destination.open("wb") as target,
            ):
                while True:
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    observed_size += len(chunk)
                    if observed_size > expected_size:
                        raise ProcessDataStructureProbeError(
                            f"Download exceeded reviewed size for {name}."
                        )
                    md5.update(chunk)
                    sha256.update(chunk)
                    target.write(chunk)
            if observed_size != expected_size:
                raise ProcessDataStructureProbeError(
                    f"Size mismatch for {name}: {observed_size} != {expected_size}."
                )
            if md5.hexdigest() != expected_md5:
                raise ProcessDataStructureProbeError(f"MD5 mismatch for {name}.")
            if sha256.hexdigest() != expected_sha256:
                raise ProcessDataStructureProbeError(f"SHA-256 mismatch for {name}.")
            return attempt
        except Exception as exc:
            last_error = exc
            destination.unlink(missing_ok=True)
            if attempt == retries:
                break
            time.sleep(min(2**attempt, 10))
    raise ProcessDataStructureProbeError(
        f"Could not verify {name} after {retries} attempts: {last_error}"
    )


def _labeldata_token_summary(item: dict[str, Any]) -> dict[str, Any]:
    files = item.get("files")
    if not isinstance(files, list) or len(files) != 50:
        raise ProcessDataStructureProbeError("Frozen LabelData must contain exactly 50 files.")
    counts: Counter[tuple[int, int]] = Counter()
    participants: set[int] = set()
    labellers: set[int] = set()
    for row in files:
        if not isinstance(row, dict):
            raise ProcessDataStructureProbeError("Malformed frozen LabelData row.")
        match = LABEL_NAME_RE.fullmatch(str(row.get("name")))
        if match is None:
            raise ProcessDataStructureProbeError(
                f"Unexpected LabelData filename {row.get('name')!r}."
            )
        participant, trial, labeller = map(int, match.groups())
        counts[(participant, trial)] += 1
        participants.add(participant)
        labellers.add(labeller)
    tokens = sorted(counts)
    return {
        "file_count": len(files),
        "recording_token_count": len(tokens),
        "participant_count": len(participants),
        "participant_indices": sorted(participants),
        "labeller_indices": sorted(labellers),
        "recording_tokens": [
            {"participant_index": participant, "trial_index": trial}
            for participant, trial in tokens
        ],
        "labeller_count_by_recording": {
            f"PrIdx_{participant}_TrIdx_{trial}": counts[(participant, trial)]
            for participant, trial in tokens
        },
    }


def _rate_summary(values: list[float]) -> dict[str, Any]:
    if not values or any(not math.isfinite(value) or value <= 0 for value in values):
        raise ProcessDataStructureProbeError("Processed timestamp-grid rates are invalid.")
    ordered = sorted(values)
    n = len(ordered)
    median = ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2
    return {
        "count": n,
        "min_hz": ordered[0],
        "median_hz": median,
        "max_hz": ordered[-1],
        "distinct_rounded_6dp_hz": sorted({round(value, 6) for value in ordered}),
    }


def build_probe(frozen_path: Path, identities_path: Path, retries: int) -> dict[str, Any]:
    frozen = _load_object(frozen_path, "frozen GIW Figshare metadata")
    ledger = _load_object(identities_path, "ProcessData exact-file identity ledger")
    identity_rows = _validate_identity_ledger(ledger)
    items = _items_by_label(frozen)
    process_item = items[PROCESS_LABEL]
    label_item = items[LABEL_LABEL]
    cleaned_item = items[EXCLUDED_LABEL]

    if process_item.get("id") != 11673645:
        raise ProcessDataStructureProbeError("Frozen ProcessData article id drifted.")
    frozen_rows = _frozen_process_rows(process_item)
    paired = _crosscheck_identity_rows(identity_rows, frozen_rows)
    label_summary = _labeldata_token_summary(label_item)

    file_results: list[dict[str, Any]] = []
    process_tokens: set[tuple[int, int]] = set()
    participants: set[int] = set()
    inferred_rates: list[float] = []
    stored_rates: list[float] = []
    scene_resolutions: Counter[tuple[int, int]] = Counter()
    total_bytes = 0

    with tempfile.TemporaryDirectory(prefix="gazeforge-giw-process-structure-") as directory:
        temp_dir = Path(directory)
        for index, (identity, frozen_row) in enumerate(paired, start=1):
            name = str(identity["name"])
            print(f"[ProcessData {index}/68] verifying {name}", flush=True)
            destination = temp_dir / name
            attempt = _download_verified(identity, frozen_row, destination, retries)
            try:
                preflight = preflight_gaze_in_wild_processdata(
                    destination,
                    expected_sha256=str(identity["sha256"]),
                    expected_bytes=int(identity["size_bytes"]),
                )
            finally:
                destination.unlink(missing_ok=True)

            filename_match = PROCESS_NAME_RE.fullmatch(name)
            if filename_match is None:
                raise ProcessDataStructureProbeError(f"Invalid ProcessData filename {name!r}.")
            filename_participant, filename_trial = map(int, filename_match.groups())
            if (
                preflight.participant_index != filename_participant
                or preflight.trial_index != filename_trial
            ):
                raise ProcessDataStructureProbeError(
                    f"Filename/internal PrIdx/TrIdx mismatch for {name}."
                )
            token = (preflight.participant_index, preflight.trial_index)
            if token in process_tokens:
                raise ProcessDataStructureProbeError(
                    f"Duplicate internal ProcessData token {token}."
                )
            process_tokens.add(token)
            participants.add(preflight.participant_index)
            inferred_rates.append(preflight.inferred_processed_rate_hz)
            stored_rates.append(preflight.stored_rate_hz)
            scene_resolutions[preflight.scene_resolution_px] += 1
            total_bytes += preflight.bytes
            file_results.append(
                {
                    "figshare_file_id": int(identity["figshare_file_id"]),
                    "name": name,
                    "size_bytes": preflight.bytes,
                    "md5": identity["md5"],
                    "sha256": preflight.sha256,
                    "download_attempt": attempt,
                    "participant_index": preflight.participant_index,
                    "trial_index": preflight.trial_index,
                    "stored_rate_hz": preflight.stored_rate_hz,
                    "inferred_processed_rate_hz": preflight.inferred_processed_rate_hz,
                    "timestamp_count": preflight.timestamp_count,
                    "timestamp_start_s": preflight.timestamp_start_s,
                    "timestamp_end_s": preflight.timestamp_end_s,
                    "por_shape": list(preflight.por_shape),
                    "confidence_shape": list(preflight.confidence_shape),
                    "scene_resolution_px": list(preflight.scene_resolution_px),
                    "labels_present": preflight.labels_present,
                    "labels_shape": (
                        list(preflight.labels_shape)
                        if preflight.labels_shape is not None
                        else None
                    ),
                    "top_level_labeldata_present": preflight.top_level_labeldata_present,
                    "adapter_coordinate_fields_compatible": (
                        preflight.adapter_coordinate_fields_compatible
                    ),
                    "timestamp_grid_valid": preflight.timestamp_grid_valid,
                    "raw_bytes_retained": False,
                }
            )
        leftovers = list(temp_dir.iterdir())
        if leftovers:
            raise ProcessDataStructureProbeError(f"Raw ProcessData cleanup failed: {leftovers}")

    if len(file_results) != 68 or len(process_tokens) != 68:
        raise ProcessDataStructureProbeError("Exact ProcessData structural coverage is incomplete.")
    if total_bytes != 2_384_573_418:
        raise ProcessDataStructureProbeError("Exact ProcessData verified byte total drifted.")
    if len(participants) != 20:
        raise ProcessDataStructureProbeError("Unexpected ProcessData participant count.")
    if any(not row["adapter_coordinate_fields_compatible"] for row in file_results):
        raise ProcessDataStructureProbeError(
            "Adapter coordinate fields failed on a ProcessData file."
        )
    if any(not row["timestamp_grid_valid"] for row in file_results):
        raise ProcessDataStructureProbeError("Timestamp grid failed on a ProcessData file.")
    if any(row["top_level_labeldata_present"] for row in file_results):
        raise ProcessDataStructureProbeError(
            "Unexpected top-level LabelData in ProcessData deposit."
        )

    label_tokens = {
        (row["participant_index"], row["trial_index"])
        for row in label_summary["recording_tokens"]
    }
    if not label_tokens.issubset(process_tokens):
        missing = sorted(label_tokens - process_tokens)
        raise ProcessDataStructureProbeError(
            f"Distributed LabelData tokens lack ProcessData matches: {missing}"
        )
    labelled_participants = {participant for participant, _ in label_tokens}
    if labelled_participants != set(label_summary["participant_indices"]):
        raise ProcessDataStructureProbeError("LabelData participant-token summary drifted.")

    download_attempts = Counter(int(row["download_attempt"]) for row in file_results)
    report: dict[str, Any] = {
        "record_type": "gaze-in-wild-exact-processdata-structure-probe-v1",
        "source_binding": {
            "figshare_project_id": 74580,
            "processdata_article_id": 11673645,
            "processdata_doi": "10.6084/m9.figshare.11673645.v1",
            "labeldata_article_id": 11673696,
            "labeldata_doi": "10.6084/m9.figshare.11673696.v1",
            "exact_byte_reviewed_evidence_fingerprint_sha256": EXPECTED_EXACT_BYTE_EVIDENCE,
            "stable_processdata_identity_fingerprint_sha256": (
                EXPECTED_STABLE_PROCESSDATA_IDENTITY
            ),
            "exact_processdata_identity_ledger_fingerprint_sha256": (
                EXPECTED_IDENTITY_EVIDENCE_FINGERPRINT
            ),
            "exact_processdata_sha256_manifest_sha256": EXPECTED_SHA256_MANIFEST,
            "frozen_figshare_metadata_source_probe_fingerprint_sha256": (
                frozen.get("source_probe_fingerprint_sha256")
            ),
        },
        "verified_processdata": {
            "file_count": len(file_results),
            "total_size_bytes": total_bytes,
            "recording_token_count": len(process_tokens),
            "participant_count": len(participants),
            "participant_indices": sorted(participants),
            "download_attempt_distribution": {
                str(key): download_attempts[key] for key in sorted(download_attempts)
            },
            "all_files_matched_frozen_size_md5_and_reviewed_sha256": True,
            "all_filename_internal_pridx_tridx_agree": True,
            "all_adapter_coordinate_fields_compatible": True,
            "all_timestamp_grids_valid": True,
            "all_raw_mat_bytes_deleted_after_inspection": True,
            "top_level_labeldata_present_in_any_processdata_file": False,
            "stored_rate_summary": _rate_summary(stored_rates),
            "inferred_processed_timestamp_grid_rate_summary": _rate_summary(inferred_rates),
            "scene_resolution_distribution": {
                f"{width}x{height}": count
                for (width, height), count in sorted(scene_resolutions.items())
            },
            "file_results": file_results,
        },
        "distributed_labeldata_pairing": {
            **label_summary,
            "all_labeldata_recording_tokens_have_processdata_match": True,
            "matched_recording_token_count": len(label_tokens),
            "processdata_tokens_without_distributed_labeldata_count": (
                len(process_tokens - label_tokens)
            ),
            "participant_disjoint_split_keys_available": len(labelled_participants) >= 2,
        },
        "excluded_cleaned_deposit": {
            "label": EXCLUDED_LABEL,
            "article_id": int(cleaned_item["id"]),
            "downloaded": False,
            "reason": "Not original-publication data; excluded by scientific source contract.",
        },
        "raw_dataset_bytes_retained": False,
        "scientific_boundary": {
            "exact_original_processdata_structure_verified": True,
            "processdata_timestamp_grid_rate_distribution_verified": True,
            "filename_internal_pridx_tridx_alignment_complete": True,
            "labeldata_processdata_recording_token_pairing_complete": True,
            "participant_disjoint_split_keys_available": len(labelled_participants) >= 2,
            "coordinate_adapter_fields_available_for_all_processdata": True,
            "coordinate_semantics_verified_for_exact_distribution": False,
            "acquisition_hardware_cadence_verified": False,
            "complete_file_to_publication_task_mapping_verified": False,
            "task_stratified_model_validation_feasible": False,
            "participant_disjoint_model_validation_created": False,
            "cross_dataset_validation_created": False,
            "gp3_validity_claim_created": False,
            "quarantine_exit_authorized": False,
            "new_model_performance_claim_created": False,
        },
        "claim_limits": [
            (
                "The timestamp-rate distribution describes the processed ProcessData.T grid "
                "only; it is not acquisition-hardware cadence."
            ),
            (
                "PrIdx/TrIdx are distribution-native identity tokens only; no publication "
                "task-name mapping is inferred."
            ),
            (
                "Availability and structural compatibility of ETG.POR do not independently "
                "establish the coordinate semantics of the exact distribution."
            ),
            (
                "Participant-disjoint split keys establish structural partitionability only; "
                "no GazeForge model has been trained, evaluated, or validated here."
            ),
            (
                "ProcessData_cleaned is excluded and no raw original-distribution MAT file is "
                "retained or redistributed."
            ),
        ],
    }
    report["structure_probe_fingerprint_sha256"] = _canonical_sha(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen", type=Path, required=True)
    parser.add_argument("--identities", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--retries", type=int, default=3)
    args = parser.parse_args()
    if args.retries < 1 or args.retries > 5:
        raise SystemExit("--retries must be between 1 and 5")
    report = build_probe(args.frozen, args.identities, args.retries)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    verified = report["verified_processdata"]
    pairing = report["distributed_labeldata_pairing"]
    print("verified_processdata_files", verified["file_count"])
    print("verified_processdata_participants", verified["participant_count"])
    print("labelled_recording_tokens", pairing["recording_token_count"])
    print("labelled_participants", pairing["participant_count"])
    print(
        "processed_rate_min_hz",
        verified["inferred_processed_timestamp_grid_rate_summary"]["min_hz"],
    )
    print(
        "processed_rate_median_hz",
        verified["inferred_processed_timestamp_grid_rate_summary"]["median_hz"],
    )
    print(
        "processed_rate_max_hz",
        verified["inferred_processed_timestamp_grid_rate_summary"]["max_hz"],
    )
    print("structure_probe_fingerprint_sha256", report["structure_probe_fingerprint_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
