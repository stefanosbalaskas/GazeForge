#!/usr/bin/env python
"""Run distribution-native human-human agreement on the verified GIW overlap subset.

The computation is deliberately label/timestamp-only.  It re-verifies every selected
LabelData file against the previously frozen candidate byte identities, validates the
internal PrIdx/TrIdx/LbrIdx scalars against the filename tokens, requires exact timestamp
identity within a recording, computes pair-specific sample and bidirectional event
agreement, and discards raw MAT files before writing the JSON summary.

No TrIdx-to-publication-task mapping, gaze-coordinate claim, model result, GP3 validity,
or quarantine exit is created by this script.
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
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.io import loadmat

from gazeforge.evaluation import sample_label_agreement
from gazeforge.event_evaluation import evaluate_event_intervals, samples_to_event_intervals
from gazeforge.gaze_in_wild import GAZE_IN_WILD_LABELS

USER_AGENT = "GazeForgeGIWLabelHHA/1.0"
CHUNK_SIZE = 4 * 1024 * 1024
LABEL_RE = re.compile(
    r"^PrIdx_(?P<participant>\d+)_TrIdx_(?P<trial>\d+)_Lbr_(?P<labeller>\d+)\.mat$"
)
EXPECTED_CANDIDATE_EVIDENCE_FINGERPRINT = (
    "46967ca0d96e0dd1c87d6f781234b1f4e3c3d8bf2318e697524c8b8b33f32a87"
)
EXPECTED_EXACT_BYTE_EVIDENCE_FINGERPRINT = (
    "dbf277d698266fe53e337a15fc342e9af1835460d2bcc69c3992635de8fa0a00"
)
EXPECTED_SELECTED_LABEL_FILE_COUNT = 18
EXPECTED_SELECTED_RECORDING_COUNT = 5
EXPECTED_PAIR_SHARED_COUNTS = {
    "1-2": 4,
    "1-5": 4,
    "1-6": 4,
    "2-5": 4,
    "2-6": 4,
    "5-6": 5,
}
EVENT_MIN_IOU = 0.50


class HHAError(RuntimeError):
    """Fail-closed error for drifting or malformed HHA input evidence."""


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
        raise HHAError(f"{path} must contain one JSON object.")
    return payload


def _load_selection(path: Path) -> dict[str, Any]:
    record = _load_json(path)
    if record.get("record_type") != "gaze-in-wild-hha-candidate-selection-evidence-v1":
        raise HHAError("Unexpected HHA candidate evidence record_type.")
    if record.get("evidence_fingerprint_sha256") != EXPECTED_CANDIDATE_EVIDENCE_FINGERPRINT:
        raise HHAError("HHA candidate evidence fingerprint does not match the reviewed value.")
    binding = record.get("source_binding")
    if not isinstance(binding, dict):
        raise HHAError("HHA candidate source binding is missing.")
    if (
        binding.get("exact_byte_reviewed_evidence_fingerprint_sha256")
        != EXPECTED_EXACT_BYTE_EVIDENCE_FINGERPRINT
    ):
        raise HHAError("HHA candidate evidence lost its exact-byte evidence binding.")
    boundary = record.get("scientific_boundary")
    if not isinstance(boundary, dict):
        raise HHAError("HHA candidate scientific boundary is missing.")
    if boundary.get("human_human_agreement_created") is not False:
        raise HHAError("Candidate evidence must not already contain HHA results.")
    if boundary.get("quarantine_exit_authorized") is not False:
        raise HHAError("Candidate evidence must keep quarantine exit closed.")
    subset = record.get("candidate_subset")
    if not isinstance(subset, dict):
        raise HHAError("HHA candidate subset is missing.")
    if subset.get("label_file_count") != EXPECTED_SELECTED_LABEL_FILE_COUNT:
        raise HHAError("Unexpected selected LabelData file count.")
    if subset.get("recording_count") != EXPECTED_SELECTED_RECORDING_COUNT:
        raise HHAError("Unexpected selected recording count.")
    return record


def _frozen_label_rows(frozen: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items = frozen.get("items")
    if not isinstance(items, list):
        raise HHAError("Frozen Figshare items are missing.")
    matches = [item for item in items if isinstance(item, dict) and item.get("label") == "LabelData"]
    if len(matches) != 1:
        raise HHAError("Expected exactly one frozen LabelData item.")
    files = matches[0].get("files")
    if not isinstance(files, list):
        raise HHAError("Frozen LabelData file list is missing.")
    result: dict[str, dict[str, Any]] = {}
    for row in files:
        if not isinstance(row, dict) or not isinstance(row.get("name"), str):
            raise HHAError("Frozen LabelData file row is invalid.")
        name = str(row["name"])
        if name in result:
            raise HHAError(f"Duplicate frozen LabelData filename: {name}.")
        result[name] = row
    return result


def _download_and_verify(
    frozen_row: dict[str, Any],
    selected_row: dict[str, Any],
    destination: Path,
    retries: int,
) -> dict[str, Any]:
    name = str(selected_row["name"])
    if frozen_row.get("name") != name:
        raise HHAError(f"Frozen filename mismatch for {name}.")
    for key in ("figshare_file_id", "size_bytes", "md5"):
        expected_key = {"figshare_file_id": "id", "size_bytes": "size", "md5": "computed_md5"}[key]
        expected = selected_row[key]
        observed = frozen_row.get(expected_key)
        if key == "md5" and isinstance(observed, str):
            observed = observed.lower()
            expected = str(expected).lower()
        if observed != expected:
            raise HHAError(f"Frozen/selected identity mismatch for {name}: {key}.")
    url = frozen_row.get("download_url")
    if not isinstance(url, str) or not url.startswith("https://"):
        raise HHAError(f"Invalid HTTPS download URL for {name}.")
    if frozen_row.get("is_link_only") is not False:
        raise HHAError(f"Refusing link-only Figshare entry {name}.")
    expected_size = int(selected_row["size_bytes"])
    expected_md5 = str(selected_row["md5"]).lower()
    expected_sha = str(selected_row["sha256"]).lower()

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        md5 = hashlib.md5(usedforsecurity=False)
        sha = hashlib.sha256()
        n_bytes = 0
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
                    n_bytes += len(chunk)
                    if n_bytes > expected_size:
                        raise HHAError(f"Downloaded bytes exceed reviewed size for {name}.")
                    md5.update(chunk)
                    sha.update(chunk)
                    handle.write(chunk)
            observed_md5 = md5.hexdigest()
            observed_sha = sha.hexdigest()
            if n_bytes != expected_size:
                raise HHAError(f"Size mismatch for {name}: {n_bytes} != {expected_size}.")
            if observed_md5 != expected_md5:
                raise HHAError(f"MD5 mismatch for {name}.")
            if observed_sha != expected_sha:
                raise HHAError(f"SHA-256 mismatch for {name}.")
            return {
                "size_bytes": n_bytes,
                "md5": observed_md5,
                "sha256": observed_sha,
                "download_attempt": attempt,
            }
        except Exception as exc:
            last_error = exc
            destination.unlink(missing_ok=True)
            if attempt == retries:
                break
            time.sleep(min(2**attempt, 10))
    raise HHAError(f"Could not verify {name} after {retries} attempts: {last_error}")


def _field(obj: Any, name: str) -> Any:
    if hasattr(obj, name):
        return getattr(obj, name)
    if isinstance(obj, np.ndarray) and obj.dtype.names and name in obj.dtype.names:
        value = obj[name]
        while isinstance(value, np.ndarray) and value.size == 1:
            value = value.reshape(-1)[0]
        return value
    raise HHAError(f"LabelData is missing required field {name!r}.")


def _scalar_int(obj: Any, name: str) -> int:
    values = np.asarray(_field(obj, name)).reshape(-1)
    if values.size != 1:
        raise HHAError(f"LabelData.{name} must be scalar.")
    value = float(values[0])
    if not np.isfinite(value) or not np.isclose(value, round(value), rtol=0.0, atol=1e-9):
        raise HHAError(f"LabelData.{name} must be a finite integer scalar.")
    return int(round(value))


def _numeric_vector(obj: Any, name: str) -> np.ndarray:
    try:
        values = np.asarray(_field(obj, name), dtype=float).reshape(-1)
    except (TypeError, ValueError) as exc:
        raise HHAError(f"LabelData.{name} must be numeric.") from exc
    if values.size == 0 or np.any(~np.isfinite(values)):
        raise HHAError(f"LabelData.{name} must be non-empty and finite.")
    return values


def _inspect_label(path: Path, name: str) -> dict[str, Any]:
    match = LABEL_RE.fullmatch(name)
    if match is None:
        raise HHAError(f"Selected LabelData filename has invalid token grammar: {name}.")
    participant = int(match.group("participant"))
    trial = int(match.group("trial"))
    labeller = int(match.group("labeller"))
    raw = loadmat(path, squeeze_me=True, struct_as_record=False)
    if "LabelData" not in raw:
        raise HHAError(f"{name} lacks MATLAB variable LabelData.")
    label_data = raw["LabelData"]
    internal_participant = _scalar_int(label_data, "PrIdx")
    internal_trial = _scalar_int(label_data, "TrIdx")
    internal_labeller = _scalar_int(label_data, "LbrIdx")
    if internal_participant != participant:
        raise HHAError(f"{name} filename/LabelData.PrIdx disagree.")
    if internal_trial != trial:
        raise HHAError(f"{name} filename/LabelData.TrIdx disagree.")
    if internal_labeller != labeller:
        raise HHAError(f"{name} filename/LabelData.LbrIdx disagree.")

    labels_raw = _numeric_vector(label_data, "Labels")
    times_s = _numeric_vector(label_data, "T")
    if labels_raw.size != times_s.size:
        raise HHAError(f"{name} Labels/T lengths differ.")
    if times_s.size < 2 or np.any(np.diff(times_s) <= 0):
        raise HHAError(f"{name} timestamps must be strictly increasing.")
    rounded = np.rint(labels_raw)
    if not np.allclose(labels_raw, rounded, rtol=0.0, atol=1e-9):
        raise HHAError(f"{name} contains non-integral event labels.")
    codes = rounded.astype(int)
    unknown = sorted(set(int(value) for value in codes) - set(GAZE_IN_WILD_LABELS))
    if unknown:
        raise HHAError(f"{name} contains unknown event codes: {unknown}.")
    rate_hz = float(1.0 / np.median(np.diff(times_s)))
    return {
        "name": name,
        "participant_id": f"PrIdx_{participant}",
        "trial_id": f"TrIdx_{trial}",
        "recording_token": f"PrIdx_{participant}_TrIdx_{trial}",
        "labeller_id": labeller,
        "n_samples": int(times_s.size),
        "sampling_rate_hz": rate_hz,
        "timestamp_sha256_float64_le": hashlib.sha256(
            np.asarray(times_s, dtype="<f8").tobytes(order="C")
        ).hexdigest(),
        "labels_sha256_int64_le": hashlib.sha256(
            np.asarray(codes, dtype="<i8").tobytes(order="C")
        ).hexdigest(),
        "times_s": times_s,
        "codes": codes,
        "filename_internal_identity_agreement": True,
    }


def _sample_frame(item: dict[str, Any]) -> pd.DataFrame:
    labels = [GAZE_IN_WILD_LABELS[int(code)] for code in item["codes"]]
    return pd.DataFrame(
        {
            "participant_id": item["participant_id"],
            "trial_id": item["trial_id"],
            "timestamp_ms": np.asarray(item["times_s"], dtype=float) * 1000.0,
            "event_label": labels,
        }
    )


def _clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _clean(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean(item) for item in value]
    if isinstance(value, tuple):
        return [_clean(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        number = float(value)
        return number if np.isfinite(number) else None
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def _event_metrics(result: Any) -> dict[str, Any]:
    clean_per_class = result.per_class.astype(object).where(pd.notna(result.per_class), None)
    return {
        "summary": _clean(dict(result.summary)),
        "per_class": _clean(clean_per_class.to_dict(orient="records")),
        "design": _clean(dict(result.design)),
    }


def _pair_metrics(
    left_id: int,
    right_id: int,
    recordings: list[str],
    indexed: dict[tuple[str, int], dict[str, Any]],
) -> dict[str, Any]:
    all_left_parts: list[pd.DataFrame] = []
    all_right_parts: list[pd.DataFrame] = []
    clear_left_parts: list[pd.DataFrame] = []
    clear_right_parts: list[pd.DataFrame] = []
    left_events_parts: list[pd.DataFrame] = []
    right_events_parts: list[pd.DataFrame] = []
    per_recording: list[dict[str, Any]] = []

    for recording in recordings:
        left = indexed[(recording, left_id)]
        right = indexed[(recording, right_id)]
        if left["n_samples"] != right["n_samples"]:
            raise HHAError(f"Sample-count drift for {recording}, pair {left_id}-{right_id}.")
        if left["timestamp_sha256_float64_le"] != right["timestamp_sha256_float64_le"]:
            raise HHAError(f"Timestamp-vector drift for {recording}, pair {left_id}-{right_id}.")
        if not np.array_equal(left["times_s"], right["times_s"]):
            raise HHAError(f"Exact timestamps differ for {recording}, pair {left_id}-{right_id}.")
        if not np.isclose(
            left["sampling_rate_hz"], right["sampling_rate_hz"], rtol=1e-9, atol=1e-9
        ):
            raise HHAError(f"Sampling-rate drift for {recording}, pair {left_id}-{right_id}.")

        left_frame = _sample_frame(left)
        right_frame = _sample_frame(right)
        all_agreement = sample_label_agreement(left_frame, right_frame)
        clear_mask = (left["codes"] != 0) & (right["codes"] != 0)
        if not bool(np.any(clear_mask)):
            raise HHAError(f"No pairwise-clearly-labelled samples for {recording}.")
        clear_left = left_frame.loc[clear_mask].reset_index(drop=True)
        clear_right = right_frame.loc[clear_mask].reset_index(drop=True)
        clear_agreement = sample_label_agreement(clear_left, clear_right)

        rate = float(left["sampling_rate_hz"])
        left_events = samples_to_event_intervals(
            left_frame,
            sampling_rate_hz=rate,
            excluded_labels=("unlabelled",),
        )
        right_events = samples_to_event_intervals(
            right_frame,
            sampling_rate_hz=rate,
            excluded_labels=("unlabelled",),
        )
        left_events_parts.append(left_events)
        right_events_parts.append(right_events)
        all_left_parts.append(left_frame)
        all_right_parts.append(right_frame)
        clear_left_parts.append(clear_left)
        clear_right_parts.append(clear_right)
        per_recording.append(
            {
                "recording_token": recording,
                "n_samples": int(left["n_samples"]),
                "sampling_rate_hz": rate,
                "pairwise_clearly_labelled_samples": int(clear_mask.sum()),
                "pairwise_clearly_labelled_fraction": float(clear_mask.mean()),
                "sample_all_labels": all_agreement,
                "sample_pairwise_clearly_labelled": clear_agreement,
                "left_event_count": int(len(left_events)),
                "right_event_count": int(len(right_events)),
            }
        )

    all_left = pd.concat(all_left_parts, ignore_index=True)
    all_right = pd.concat(all_right_parts, ignore_index=True)
    clear_left = pd.concat(clear_left_parts, ignore_index=True)
    clear_right = pd.concat(clear_right_parts, ignore_index=True)
    left_events = pd.concat(left_events_parts, ignore_index=True)
    right_events = pd.concat(right_events_parts, ignore_index=True)

    all_agreement = sample_label_agreement(all_left, all_right)
    clear_agreement = sample_label_agreement(clear_left, clear_right)
    left_reference = evaluate_event_intervals(
        predicted=right_events,
        reference=left_events,
        min_iou=EVENT_MIN_IOU,
        require_label_match=True,
    )
    right_reference = evaluate_event_intervals(
        predicted=left_events,
        reference=right_events,
        min_iou=EVENT_MIN_IOU,
        require_label_match=True,
    )
    return {
        "left_labeller_id": left_id,
        "right_labeller_id": right_id,
        "shared_recording_count": len(recordings),
        "shared_recordings": recordings,
        "n_aligned_samples": int(len(all_left)),
        "n_pairwise_clearly_labelled_samples": int(len(clear_left)),
        "pairwise_clearly_labelled_fraction": float(len(clear_left) / len(all_left)),
        "sample_agreement_all_labels": _clean(all_agreement),
        "sample_agreement_pairwise_clearly_labelled": _clean(clear_agreement),
        "event_agreement_left_as_reference": _event_metrics(left_reference),
        "event_agreement_right_as_reference": _event_metrics(right_reference),
        "per_recording": _clean(per_recording),
    }


def run_discovery(
    selection_path: Path,
    frozen_path: Path,
    output_path: Path,
    retries: int,
) -> dict[str, Any]:
    selection = _load_selection(selection_path)
    frozen = _load_json(frozen_path)
    frozen_rows = _frozen_label_rows(frozen)
    subset = selection["candidate_subset"]
    selected_rows = subset["label_files"]
    if not isinstance(selected_rows, list) or len(selected_rows) != EXPECTED_SELECTED_LABEL_FILE_COUNT:
        raise HHAError("Selected LabelData inventory is malformed.")

    inspected: list[dict[str, Any]] = []
    verification_rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="gazeforge-giw-hha-") as tmp:
        root = Path(tmp)
        for index, selected in enumerate(selected_rows, start=1):
            if not isinstance(selected, dict):
                raise HHAError("Selected LabelData row is malformed.")
            name = str(selected["name"])
            if name not in frozen_rows:
                raise HHAError(f"Selected LabelData file is absent from frozen metadata: {name}.")
            path = root / f"{int(selected['figshare_file_id'])}-{name}"
            print(f"[HHA LabelData {index}/{len(selected_rows)}] verifying {name}", flush=True)
            identity = _download_and_verify(frozen_rows[name], selected, path, retries)
            try:
                item = _inspect_label(path, name)
            finally:
                path.unlink(missing_ok=True)
            inspected.append(item)
            verification_rows.append(
                {
                    "name": name,
                    "figshare_file_id": int(selected["figshare_file_id"]),
                    "size_bytes": int(identity["size_bytes"]),
                    "md5": identity["md5"],
                    "sha256": identity["sha256"],
                    "download_attempt": int(identity["download_attempt"]),
                    "participant_id": item["participant_id"],
                    "trial_id": item["trial_id"],
                    "recording_token": item["recording_token"],
                    "labeller_id": int(item["labeller_id"]),
                    "n_samples": int(item["n_samples"]),
                    "sampling_rate_hz": float(item["sampling_rate_hz"]),
                    "timestamp_sha256_float64_le": item["timestamp_sha256_float64_le"],
                    "labels_sha256_int64_le": item["labels_sha256_int64_le"],
                    "filename_internal_identity_agreement": True,
                    "raw_bytes_retained": False,
                }
            )
        if any(root.iterdir()):
            raise HHAError("Raw LabelData bytes remained in the temporary HHA directory.")

    indexed = {(item["recording_token"], int(item["labeller_id"])): item for item in inspected}
    if len(indexed) != len(inspected):
        raise HHAError("Duplicate recording/labeller identity in selected HHA subset.")
    by_labeller: dict[int, set[str]] = defaultdict(set)
    for item in inspected:
        by_labeller[int(item["labeller_id"])].add(str(item["recording_token"]))

    pair_results: list[dict[str, Any]] = []
    observed_pair_counts: dict[str, int] = {}
    for left_id, right_id in itertools.combinations(sorted(by_labeller), 2):
        shared = sorted(by_labeller[left_id] & by_labeller[right_id])
        if not shared:
            continue
        pair_key = f"{left_id}-{right_id}"
        observed_pair_counts[pair_key] = len(shared)
        pair_results.append(_pair_metrics(left_id, right_id, shared, indexed))
    if observed_pair_counts != EXPECTED_PAIR_SHARED_COUNTS:
        raise HHAError(
            f"Distributed pair coverage drifted: {observed_pair_counts} != "
            f"{EXPECTED_PAIR_SHARED_COUNTS}."
        )

    record: dict[str, Any] = {
        "record_type": "gaze-in-wild-distributed-overlap-human-human-agreement-discovery-v1",
        "source_binding": {
            "candidate_selection_evidence_path": selection_path.as_posix(),
            "candidate_selection_evidence_fingerprint_sha256": (
                EXPECTED_CANDIDATE_EVIDENCE_FINGERPRINT
            ),
            "exact_byte_reviewed_evidence_fingerprint_sha256": (
                EXPECTED_EXACT_BYTE_EVIDENCE_FINGERPRINT
            ),
            "frozen_figshare_metadata_path": frozen_path.as_posix(),
        },
        "input_verification": {
            "selected_label_file_count": len(verification_rows),
            "selected_recording_count": len({row["recording_token"] for row in verification_rows}),
            "all_files_matched_prior_size_md5_sha256": True,
            "all_filename_internal_pridx_tridx_lbridx_agree": True,
            "all_raw_mat_bytes_deleted_after_inspection": True,
            "verification_manifest_sha256": _canonical_sha(verification_rows),
            "files": verification_rows,
        },
        "analysis_design": {
            "scope": "distributed_multi_labeller_overlap_subset_only",
            "pair_shared_recording_counts": observed_pair_counts,
            "sample_all_labels_includes_unlabelled_code_0": True,
            "pairwise_clearly_labelled_definition": (
                "retain a sample only when both selected labellers have nonzero label codes"
            ),
            "event_unlabelled_code_0_policy": "hard_separator_and_excluded_event_class",
            "event_min_iou": EVENT_MIN_IOU,
            "event_label_match_required": True,
            "event_metrics_bidirectional": True,
            "neither_labeller_treated_as_truth": True,
            "sampling_rate_policy": "timestamp_inferred_per_recording",
            "resampling": None,
            "coordinate_data_used": False,
            "processdata_loaded": False,
            "tridx_to_publication_task_mapping_used": False,
        },
        "pair_results": _clean(pair_results),
        "scientific_boundary": {
            "human_human_agreement_created_for_distributed_overlap_subset": True,
            "full_distributed_labeldata_hha_created": False,
            "task_stratified_hha_created": False,
            "gaze_coordinate_validation_created": False,
            "participant_disjoint_model_validation_created": False,
            "cross_dataset_validation_created": False,
            "gp3_validity_claim_created": False,
            "complete_file_to_publication_task_mapping_verified": False,
            "quarantine_exit_authorized": False,
            "new_model_performance_claim_created": False,
        },
        "raw_dataset_bytes_retained": False,
    }
    record["discovery_fingerprint_sha256"] = _canonical_sha(record)
    output_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--frozen", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--retries", type=int, default=3)
    args = parser.parse_args()
    if args.retries < 1:
        raise SystemExit("--retries must be >= 1")
    record = run_discovery(args.selection, args.frozen, args.output, args.retries)
    print("selected_label_files", record["input_verification"]["selected_label_file_count"])
    print("selected_recordings", record["input_verification"]["selected_recording_count"])
    print("labeller_pairs", len(record["pair_results"]))
    print("discovery_fingerprint_sha256", record["discovery_fingerprint_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
