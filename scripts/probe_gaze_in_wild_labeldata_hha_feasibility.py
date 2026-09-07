#!/usr/bin/env python
"""Inspect verified GIW LabelData for human-human agreement feasibility.

This probe intentionally treats PrIdx, TrIdx, and Lbr only as distribution filename
tokens. It does not map TrIdx to publication tasks and does not compute an empirical
human-human agreement result. Raw MAT files are deleted immediately after inspection.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
import tempfile
import time
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import loadmat

USER_AGENT = "GazeForgeLabelDataHHAFeasibility/1.0"
CHUNK_SIZE = 4 * 1024 * 1024
LABEL_RE = re.compile(
    r"^PrIdx_(?P<participant>\d+)_TrIdx_(?P<trial>\d+)_Lbr_(?P<labeller>\d+)\.mat$"
)
EXPECTED_LABELDATA_FILE_COUNT = 50
EXPECTED_LABELDATA_TOTAL_BYTES = 28_725_824
EXPECTED_LABELDATA_ARTICLE_ID = 11673696
EXPECTED_LABELDATA_DOI = "10.6084/m9.figshare.11673696.v1"
EXPECTED_EXACT_BYTE_EVIDENCE_FINGERPRINT = (
    "dbf277d698266fe53e337a15fc342e9af1835460d2bcc69c3992635de8fa0a00"
)


class LabelDataFeasibilityError(RuntimeError):
    """Fail-closed error for malformed or drifting LabelData evidence."""


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise LabelDataFeasibilityError(f"{path} must contain one JSON object.")
    return payload


def _item_by_label(frozen: dict[str, Any], label: str) -> dict[str, Any]:
    items = frozen.get("items")
    if not isinstance(items, list):
        raise LabelDataFeasibilityError("Frozen Figshare metadata items are missing.")
    matches = [item for item in items if isinstance(item, dict) and item.get("label") == label]
    if len(matches) != 1:
        raise LabelDataFeasibilityError(f"Expected exactly one frozen {label} item.")
    return matches[0]


def _expected_md5(row: dict[str, Any]) -> str:
    supplied = row.get("supplied_md5")
    computed = row.get("computed_md5")
    if not isinstance(supplied, str) or not isinstance(computed, str):
        raise LabelDataFeasibilityError(f"Missing MD5 metadata for {row.get('name')}.")
    if supplied.lower() != computed.lower() or len(supplied) != 32:
        raise LabelDataFeasibilityError(f"Frozen MD5 metadata drifted for {row.get('name')}.")
    return supplied.lower()


def _download_verified(row: dict[str, Any], destination: Path, retries: int) -> dict[str, Any]:
    name = str(row.get("name"))
    url = row.get("download_url")
    expected_size = row.get("size")
    if not isinstance(url, str) or not url.startswith("https://"):
        raise LabelDataFeasibilityError(f"Invalid HTTPS download URL for {name}.")
    if not isinstance(expected_size, int) or expected_size <= 0:
        raise LabelDataFeasibilityError(f"Invalid frozen byte count for {name}.")
    if row.get("is_link_only") is not False:
        raise LabelDataFeasibilityError(f"Refusing link-only Figshare entry {name}.")
    expected_md5 = _expected_md5(row)

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        md5 = hashlib.md5(usedforsecurity=False)
        sha256 = hashlib.sha256()
        observed_size = 0
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with (
                urllib.request.urlopen(request, timeout=180) as response,
                destination.open("wb") as handle,
            ):
                while True:
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    observed_size += len(chunk)
                    if observed_size > expected_size:
                        raise LabelDataFeasibilityError(
                            f"Downloaded bytes exceed frozen size for {name}."
                        )
                    md5.update(chunk)
                    sha256.update(chunk)
                    handle.write(chunk)
            if observed_size != expected_size:
                raise LabelDataFeasibilityError(
                    f"Size mismatch for {name}: {observed_size} != {expected_size}."
                )
            observed_md5 = md5.hexdigest()
            if observed_md5 != expected_md5:
                raise LabelDataFeasibilityError(
                    f"MD5 mismatch for {name}: {observed_md5} != {expected_md5}."
                )
            return {
                "size_bytes": observed_size,
                "md5": observed_md5,
                "sha256": sha256.hexdigest(),
                "download_attempt": attempt,
            }
        except Exception as exc:
            last_error = exc
            destination.unlink(missing_ok=True)
            if attempt == retries:
                break
            time.sleep(min(2**attempt, 10))
    raise LabelDataFeasibilityError(
        f"Could not verify {name} after {retries} attempts: {last_error}"
    )


def _field_names(value: Any) -> list[str]:
    names = getattr(value, "_fieldnames", None)
    if names is not None:
        return sorted(str(name) for name in names)
    dtype = getattr(value, "dtype", None)
    dtype_names = getattr(dtype, "names", None)
    if dtype_names:
        return sorted(str(name) for name in dtype_names)
    raise LabelDataFeasibilityError("LabelData is not an inspectable MATLAB struct.")


def _field(value: Any, name: str) -> Any:
    if hasattr(value, name):
        return getattr(value, name)
    if isinstance(value, np.ndarray) and value.dtype.names and name in value.dtype.names:
        result = value[name]
        while isinstance(result, np.ndarray) and result.size == 1:
            result = result.reshape(-1)[0]
        return result
    raise LabelDataFeasibilityError(f"LabelData is missing required field {name!r}.")


def _numeric_vector(value: Any, name: str) -> np.ndarray:
    try:
        array = np.asarray(value, dtype=float).reshape(-1)
    except (TypeError, ValueError) as exc:
        raise LabelDataFeasibilityError(f"LabelData.{name} must be numeric.") from exc
    if array.size == 0 or np.any(~np.isfinite(array)):
        raise LabelDataFeasibilityError(f"LabelData.{name} must be non-empty and finite.")
    return array


def _float64_sha(values: np.ndarray) -> str:
    stable = np.asarray(values, dtype="<f8")
    return hashlib.sha256(stable.tobytes(order="C")).hexdigest()


def _inspect_label_file(path: Path, filename_labeller: int) -> dict[str, Any]:
    raw = loadmat(path, squeeze_me=True, struct_as_record=False)
    if "LabelData" not in raw:
        raise LabelDataFeasibilityError(f"{path.name} lacks the LabelData variable.")
    label_data = raw["LabelData"]
    fields = _field_names(label_data)
    labels = _numeric_vector(_field(label_data, "Labels"), "Labels")
    times = _numeric_vector(_field(label_data, "T"), "T")
    if labels.size != times.size:
        raise LabelDataFeasibilityError(f"{path.name} Labels/T lengths differ.")
    if times.size < 2 or np.any(np.diff(times) <= 0):
        raise LabelDataFeasibilityError(f"{path.name} timestamps are not strictly increasing.")
    rounded_labels = np.rint(labels)
    if not np.allclose(labels, rounded_labels, rtol=0.0, atol=1e-9):
        raise LabelDataFeasibilityError(f"{path.name} contains non-integral label codes.")
    label_codes = rounded_labels.astype(int)

    struct_labeller: int | None = None
    if "LbrIdx" in fields:
        raw_labeller = np.asarray(_field(label_data, "LbrIdx")).reshape(-1)
        if raw_labeller.size != 1:
            raise LabelDataFeasibilityError(f"{path.name} LabelData.LbrIdx is not scalar.")
        struct_labeller = int(raw_labeller[0])
        if struct_labeller != filename_labeller:
            raise LabelDataFeasibilityError(
                f"{path.name} filename/LabelData.LbrIdx disagree: "
                f"{filename_labeller} != {struct_labeller}."
            )

    diffs = np.diff(times)
    median_dt = float(np.median(diffs))
    rate = float(1.0 / median_dt)
    counts = Counter(int(code) for code in label_codes)
    return {
        "mat_struct_fields": fields,
        "n_samples": int(times.size),
        "timestamp_sha256_float64_le": _float64_sha(times),
        "labels_sha256_int64_le": hashlib.sha256(
            np.asarray(label_codes, dtype="<i8").tobytes(order="C")
        ).hexdigest(),
        "first_timestamp_s": float(times[0]),
        "last_timestamp_s": float(times[-1]),
        "median_dt_s": median_dt,
        "min_dt_s": float(np.min(diffs)),
        "max_dt_s": float(np.max(diffs)),
        "inferred_sampling_rate_hz": rate,
        "label_code_counts": {str(code): counts[code] for code in sorted(counts)},
        "filename_labeller_id": filename_labeller,
        "struct_labeller_id": struct_labeller,
        "filename_struct_labeller_agree": (
            struct_labeller is None or struct_labeller == filename_labeller
        ),
    }


def _process_names(item: dict[str, Any]) -> set[str]:
    files = item.get("files")
    if not isinstance(files, list):
        raise LabelDataFeasibilityError("Frozen ProcessData file list is missing.")
    return {
        str(row.get("name"))
        for row in files
        if isinstance(row, dict) and isinstance(row.get("name"), str)
    }


def _pair_coverage(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_labeller: dict[int, set[str]] = defaultdict(set)
    for row in rows:
        by_labeller[int(row["labeller_id"])].add(str(row["recording_token"]))
    result: list[dict[str, Any]] = []
    for left, right in itertools.combinations(sorted(by_labeller), 2):
        left_set = by_labeller[left]
        right_set = by_labeller[right]
        shared = sorted(left_set & right_set)
        result.append(
            {
                "left_labeller_id": left,
                "right_labeller_id": right,
                "left_recording_count": len(left_set),
                "right_recording_count": len(right_set),
                "shared_recording_count": len(shared),
                "shared_recordings": shared,
                "left_only_recordings": sorted(left_set - right_set),
                "right_only_recordings": sorted(right_set - left_set),
                "complete_overlap_across_full_distributed_labeller_inventories": (
                    left_set == right_set
                ),
            }
        )
    return result


def _group_recordings(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row["recording_token"])].append(row)

    result: list[dict[str, Any]] = []
    for recording in sorted(groups):
        members = sorted(groups[recording], key=lambda row: int(row["labeller_id"]))
        timestamps = {str(row["timestamp_sha256_float64_le"]) for row in members}
        sample_counts = {int(row["n_samples"]) for row in members}
        process_names = {str(row["process_filename"]) for row in members}
        rates = [float(row["inferred_sampling_rate_hz"]) for row in members]
        same_rate = bool(np.allclose(rates, rates[0], rtol=1e-9, atol=1e-9))
        has_multiple = len(members) >= 2
        pairing_verified = bool(
            has_multiple
            and len(timestamps) == 1
            and len(sample_counts) == 1
            and len(process_names) == 1
            and same_rate
        )
        result.append(
            {
                "recording_token": recording,
                "participant_token": members[0]["participant_token"],
                "trial_token": members[0]["trial_token"],
                "process_filename": members[0]["process_filename"],
                "labeller_ids": [int(row["labeller_id"]) for row in members],
                "labeller_count": len(members),
                "n_samples": members[0]["n_samples"] if len(sample_counts) == 1 else None,
                "all_labellers_share_exact_timestamp_vector": len(timestamps) == 1,
                "all_labellers_share_sample_count": len(sample_counts) == 1,
                "all_labellers_resolve_to_same_process_file": len(process_names) == 1,
                "all_labellers_share_inferred_sampling_rate": same_rate,
                "distribution_level_hha_pairing_preconditions_verified": pairing_verified,
            }
        )
    return result


def run_probe(frozen_path: Path, output_path: Path, retries: int) -> dict[str, Any]:
    frozen = _load_json(frozen_path)
    label_item = _item_by_label(frozen, "LabelData")
    process_item = _item_by_label(frozen, "ProcessData")
    if int(label_item.get("id", -1)) != EXPECTED_LABELDATA_ARTICLE_ID:
        raise LabelDataFeasibilityError("Frozen LabelData article id drifted.")
    if label_item.get("doi") != EXPECTED_LABELDATA_DOI:
        raise LabelDataFeasibilityError("Frozen LabelData DOI drifted.")
    files = label_item.get("files")
    if not isinstance(files, list) or len(files) != EXPECTED_LABELDATA_FILE_COUNT:
        raise LabelDataFeasibilityError("Frozen LabelData file count drifted.")
    expected_total = int(label_item.get("total_size_bytes", -1))
    if expected_total != EXPECTED_LABELDATA_TOTAL_BYTES:
        raise LabelDataFeasibilityError("Frozen LabelData total byte count drifted.")
    process_names = _process_names(process_item)

    rows: list[dict[str, Any]] = []
    observed_total = 0
    with tempfile.TemporaryDirectory(prefix="gazeforge-giw-labeldata-") as tmp:
        temp_root = Path(tmp)
        for index, frozen_row in enumerate(files, start=1):
            if not isinstance(frozen_row, dict):
                raise LabelDataFeasibilityError("Frozen LabelData row is invalid.")
            name = str(frozen_row.get("name"))
            match = LABEL_RE.fullmatch(name)
            if match is None:
                raise LabelDataFeasibilityError(
                    f"LabelData filename does not match frozen token grammar: {name}."
                )
            participant = int(match.group("participant"))
            trial = int(match.group("trial"))
            labeller = int(match.group("labeller"))
            recording = f"PrIdx_{participant}_TrIdx_{trial}"
            process_filename = f"{recording}.mat"
            if process_filename not in process_names:
                raise LabelDataFeasibilityError(
                    f"{name} does not resolve to a frozen original ProcessData file."
                )
            destination = temp_root / f"{int(frozen_row['id'])}-{name}"
            print(f"[LabelData {index}/{len(files)}] inspecting {name}", flush=True)
            identity = _download_verified(frozen_row, destination, retries)
            try:
                structural = _inspect_label_file(destination, labeller)
            finally:
                destination.unlink(missing_ok=True)
            observed_total += int(identity["size_bytes"])
            rows.append(
                {
                    "figshare_file_id": int(frozen_row["id"]),
                    "name": name,
                    "size_bytes": identity["size_bytes"],
                    "md5": identity["md5"],
                    "sha256": identity["sha256"],
                    "download_attempt": identity["download_attempt"],
                    "participant_token": f"PrIdx_{participant}",
                    "trial_token": f"TrIdx_{trial}",
                    "recording_token": recording,
                    "labeller_id": labeller,
                    "process_filename": process_filename,
                    "process_file_present_in_frozen_original_manifest": True,
                    "raw_bytes_retained": False,
                    **structural,
                }
            )
        if any(temp_root.iterdir()):
            raise LabelDataFeasibilityError("Raw LabelData bytes remained in the temporary tree.")

    if observed_total != EXPECTED_LABELDATA_TOTAL_BYTES:
        raise LabelDataFeasibilityError("Verified LabelData total bytes drifted.")

    recording_groups = _group_recordings(rows)
    multi = [row for row in recording_groups if int(row["labeller_count"]) >= 2]
    eligible = [
        row
        for row in recording_groups
        if row["distribution_level_hha_pairing_preconditions_verified"] is True
    ]
    field_schemas = sorted({tuple(row["mat_struct_fields"]) for row in rows})
    labellers = sorted({int(row["labeller_id"]) for row in rows})
    content_manifest_rows = [
        {
            "figshare_file_id": row["figshare_file_id"],
            "name": row["name"],
            "size_bytes": row["size_bytes"],
            "md5": row["md5"],
            "sha256": row["sha256"],
            "timestamp_sha256_float64_le": row["timestamp_sha256_float64_le"],
            "labels_sha256_int64_le": row["labels_sha256_int64_le"],
            "process_filename": row["process_filename"],
            "raw_bytes_retained": False,
        }
        for row in rows
    ]
    record: dict[str, Any] = {
        "record_type": "gaze-in-wild-labeldata-hha-feasibility-probe-v1",
        "source_binding": {
            "labeldata_article_id": EXPECTED_LABELDATA_ARTICLE_ID,
            "labeldata_doi": EXPECTED_LABELDATA_DOI,
            "exact_byte_reviewed_evidence_fingerprint_sha256": (
                EXPECTED_EXACT_BYTE_EVIDENCE_FINGERPRINT
            ),
            "frozen_metadata_path": frozen_path.as_posix(),
        },
        "verified_labeldata": {
            "file_count": len(rows),
            "total_size_bytes": observed_total,
            "all_files_matched_frozen_size_and_md5": True,
            "all_files_resolve_to_frozen_original_processdata": True,
            "all_raw_mat_bytes_deleted_after_inspection": True,
            "labeller_ids": labellers,
            "distinct_labeldata_field_schemas": [list(schema) for schema in field_schemas],
            "content_manifest_sha256": _canonical_sha(content_manifest_rows),
            "files": rows,
        },
        "recording_pairing": {
            "recording_count": len(recording_groups),
            "multi_labeller_recording_count": len(multi),
            "pairing_preconditions_verified_recording_count": len(eligible),
            "multi_labeller_recordings": [row["recording_token"] for row in multi],
            "pairing_preconditions_verified_recordings": [
                row["recording_token"] for row in eligible
            ],
            "recordings": recording_groups,
            "labeller_pair_coverage": _pair_coverage(rows),
        },
        "interpretation": {
            "filename_tokens_are_distribution_identifiers_only": True,
            "tridx_to_publication_task_mapping_inferred": False,
            "participant_publication_identity_claim_created": False,
            "hha_can_be_attempted_for_verified_multi_labeller_recordings": bool(eligible),
            "hha_metrics_created": False,
            "task_stratified_hha_authorized": False,
        },
        "scientific_boundary": {
            "exact_labeldata_bytes_reverified": True,
            "distribution_level_pairing_feasibility_inspected": True,
            "human_human_agreement_created": False,
            "participant_disjoint_model_validation_created": False,
            "cross_dataset_validation_created": False,
            "gp3_validity_claim_created": False,
            "complete_file_to_publication_task_mapping_verified": False,
            "quarantine_exit_authorized": False,
            "new_empirical_performance_claim_created": False,
        },
        "raw_dataset_bytes_retained": False,
    }
    record["probe_fingerprint_sha256"] = _canonical_sha(record)
    output_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--retries", type=int, default=3)
    args = parser.parse_args()
    if args.retries < 1:
        raise SystemExit("--retries must be >= 1")
    record = run_probe(args.frozen, args.output, args.retries)
    pairing = record["recording_pairing"]
    print("verified_labeldata_files", record["verified_labeldata"]["file_count"])
    print("verified_labeldata_bytes", record["verified_labeldata"]["total_size_bytes"])
    print("recordings", pairing["recording_count"])
    print("multi_labeller_recordings", pairing["multi_labeller_recording_count"])
    print(
        "pairing_preconditions_verified_recordings",
        pairing["pairing_preconditions_verified_recording_count"],
    )
    print("probe_fingerprint_sha256", record["probe_fingerprint_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
