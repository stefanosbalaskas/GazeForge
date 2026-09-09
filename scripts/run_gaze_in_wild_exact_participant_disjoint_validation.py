#!/usr/bin/env python
"""Run task-agnostic participant-disjoint validation on exact original GIW bytes."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any

from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_exact_validation import (
    EXECUTION_PROTOCOL_FINGERPRINT,
    REFERENCE_MANIFEST_FINGERPRINT,
    assemble_exact_gaze_in_wild_benchmark,
    prepare_exact_gaze_in_wild_recording,
    run_exact_gaze_in_wild_model_validation,
    validate_exact_execution_protocol,
    validate_exact_reference_manifest,
)

USER_AGENT = "GazeForgeGIWExactParticipantDisjointValidation/1.0"
CHUNK_SIZE = 4 * 1024 * 1024
EXPECTED_PROCESS_LEDGER_TYPE = "gaze-in-wild-processdata-exact-sha256-ledger-v1"
EXPECTED_PROCESS_LEDGER_FINGERPRINT = (
    "85f131389315a1185e3a8973629c8e5ee3417bb73704de8054366e508af0a2e2"
)
EXPECTED_PROCESS_SHA_MANIFEST = (
    "162bf688fbd0bfdaf79a11d423f3689abd31bea9a4e8423bc03020ebd598354d"
)


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise BenchmarkIntegrityError(f"{path} must contain one JSON object.")
    return value


def _item_by_label(frozen: dict[str, Any], label: str) -> dict[str, Any]:
    items = frozen.get("items")
    if not isinstance(items, list):
        raise BenchmarkIntegrityError("Frozen GIW Figshare metadata items are missing.")
    matches = [row for row in items if isinstance(row, dict) and row.get("label") == label]
    if len(matches) != 1:
        raise BenchmarkIntegrityError(f"Expected exactly one frozen GIW {label} item.")
    return matches[0]


def _files_by_name(item: dict[str, Any]) -> dict[str, dict[str, Any]]:
    files = item.get("files")
    if not isinstance(files, list):
        raise BenchmarkIntegrityError("Frozen GIW Figshare file list is missing.")
    result: dict[str, dict[str, Any]] = {}
    for value in files:
        if not isinstance(value, dict) or not isinstance(value.get("name"), str):
            raise BenchmarkIntegrityError("Malformed frozen GIW Figshare file row.")
        name = str(value["name"])
        if name in result:
            raise BenchmarkIntegrityError(f"Duplicate frozen GIW filename {name}.")
        result[name] = value
    return result


def _expected_md5(row: dict[str, Any]) -> str:
    supplied = row.get("supplied_md5")
    computed = row.get("computed_md5")
    if not isinstance(supplied, str) or not isinstance(computed, str):
        raise BenchmarkIntegrityError(f"Missing frozen MD5 for {row.get('name')}.")
    if supplied.lower() != computed.lower() or len(supplied) != 32:
        raise BenchmarkIntegrityError(f"Frozen MD5 drifted for {row.get('name')}.")
    return supplied.lower()


def _process_sha_map(payload: dict[str, Any]) -> dict[str, str]:
    record = dict(payload)
    stored = str(record.pop("evidence_fingerprint_sha256", ""))
    if record.get("record_type") != EXPECTED_PROCESS_LEDGER_TYPE:
        raise BenchmarkIntegrityError("Unexpected GIW ProcessData exact identity ledger type.")
    if stored != EXPECTED_PROCESS_LEDGER_FINGERPRINT:
        raise BenchmarkIntegrityError("GIW ProcessData exact identity ledger fingerprint drifted.")
    if benchmark_fingerprint(record) != EXPECTED_PROCESS_LEDGER_FINGERPRINT:
        raise BenchmarkIntegrityError("GIW ProcessData exact identity ledger body drifted.")
    files = record.get("files")
    if not isinstance(files, list) or len(files) != 68:
        raise BenchmarkIntegrityError("GIW ProcessData identity ledger requires 68 files.")
    rows: list[dict[str, str]] = []
    result: dict[str, str] = {}
    for value in files:
        if not isinstance(value, dict):
            raise BenchmarkIntegrityError("Malformed GIW ProcessData identity row.")
        name = value.get("name")
        sha256 = value.get("sha256")
        if not isinstance(name, str) or not isinstance(sha256, str) or len(sha256) != 64:
            raise BenchmarkIntegrityError("Malformed GIW ProcessData exact identity.")
        if name in result:
            raise BenchmarkIntegrityError(f"Duplicate GIW ProcessData identity {name}.")
        result[name] = sha256
        rows.append({"name": name, "sha256": sha256})
    if benchmark_fingerprint(rows) != EXPECTED_PROCESS_SHA_MANIFEST:
        raise BenchmarkIntegrityError("GIW ProcessData SHA-256 manifest drifted.")
    if record.get("sha256_manifest_sha256") != EXPECTED_PROCESS_SHA_MANIFEST:
        raise BenchmarkIntegrityError("Stored GIW ProcessData SHA-256 manifest drifted.")
    return result


def _download_verified(
    frozen: dict[str, Any],
    destination: Path,
    *,
    expected_sha256: str,
    retries: int,
) -> dict[str, Any]:
    name = str(frozen.get("name"))
    url = frozen.get("download_url")
    size = frozen.get("size")
    if not isinstance(url, str) or not url.startswith("https://"):
        raise BenchmarkIntegrityError(f"Invalid GIW HTTPS download URL for {name}.")
    if not isinstance(size, int) or size <= 0:
        raise BenchmarkIntegrityError(f"Invalid GIW frozen byte count for {name}.")
    if frozen.get("is_link_only") is not False:
        raise BenchmarkIntegrityError(f"Refusing link-only GIW file {name}.")
    expected_md5 = _expected_md5(frozen)
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        md5 = hashlib.md5(usedforsecurity=False)
        sha256 = hashlib.sha256()
        observed = 0
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
                    observed += len(chunk)
                    if observed > size:
                        raise BenchmarkIntegrityError(
                            f"GIW download exceeded frozen byte count for {name}."
                        )
                    md5.update(chunk)
                    sha256.update(chunk)
                    handle.write(chunk)
            if observed != size:
                raise BenchmarkIntegrityError(
                    f"GIW size mismatch for {name}: {observed} != {size}."
                )
            if md5.hexdigest() != expected_md5:
                raise BenchmarkIntegrityError(f"GIW MD5 mismatch for {name}.")
            if sha256.hexdigest() != expected_sha256:
                raise BenchmarkIntegrityError(f"GIW SHA-256 mismatch for {name}.")
            return {
                "name": name,
                "figshare_file_id": int(frozen["id"]),
                "size_bytes": observed,
                "md5": md5.hexdigest(),
                "sha256": sha256.hexdigest(),
                "download_attempt": attempt,
            }
        except Exception as exc:
            last_error = exc
            destination.unlink(missing_ok=True)
            if attempt == retries:
                break
            time.sleep(min(2**attempt, 10))
    raise BenchmarkIntegrityError(
        f"Could not verify exact GIW file {name} after {retries} attempts: {last_error}"
    )


def run(
    *,
    frozen_path: Path,
    reference_manifest_path: Path,
    execution_protocol_path: Path,
    process_identity_path: Path,
    output_path: Path,
    retries: int,
) -> dict[str, Any]:
    frozen = _load_json(frozen_path)
    reference_manifest = validate_exact_reference_manifest(_load_json(reference_manifest_path))
    execution_protocol = validate_exact_execution_protocol(_load_json(execution_protocol_path))
    process_sha = _process_sha_map(_load_json(process_identity_path))
    label_rows = _files_by_name(_item_by_label(frozen, "LabelData"))
    process_rows = _files_by_name(_item_by_label(frozen, "ProcessData"))
    cleaned = _item_by_label(frozen, "ProcessData_cleaned")

    selected_files = reference_manifest["selected_reference"]["files"]
    parts = []
    file_reports: list[dict[str, Any]] = []
    download_reports: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="gazeforge-giw-exact-validation-") as directory:
        temp_root = Path(directory)
        for index, manifest_row in enumerate(selected_files, start=1):
            if not isinstance(manifest_row, dict):
                raise BenchmarkIntegrityError("Malformed GIW selected-reference manifest row.")
            label_name = str(manifest_row["name"])
            process_name = str(manifest_row["process_filename"])
            if label_name not in label_rows or process_name not in process_rows:
                raise BenchmarkIntegrityError("GIW selected pair is absent from frozen metadata.")
            if process_name not in process_sha:
                raise BenchmarkIntegrityError("GIW selected ProcessData lacks exact SHA-256.")
            frozen_label = label_rows[label_name]
            frozen_process = process_rows[process_name]
            if int(frozen_label["id"]) != int(manifest_row["figshare_file_id"]):
                raise BenchmarkIntegrityError("GIW selected LabelData Figshare id drifted.")
            if int(frozen_label["size"]) != int(manifest_row["size_bytes"]):
                raise BenchmarkIntegrityError("GIW selected LabelData byte count drifted.")
            if _expected_md5(frozen_label) != str(manifest_row["md5"]):
                raise BenchmarkIntegrityError("GIW selected LabelData MD5 drifted.")

            label_path = temp_root / label_name
            process_path = temp_root / process_name
            print(f"[GIW exact {index}/18] verifying {label_name} + {process_name}", flush=True)
            label_download = _download_verified(
                frozen_label,
                label_path,
                expected_sha256=str(manifest_row["sha256"]),
                retries=retries,
            )
            process_download = _download_verified(
                frozen_process,
                process_path,
                expected_sha256=process_sha[process_name],
                retries=retries,
            )
            try:
                part, report = prepare_exact_gaze_in_wild_recording(
                    label_path,
                    process_path,
                    manifest_row,
                    execution_protocol,
                )
            finally:
                label_path.unlink(missing_ok=True)
                process_path.unlink(missing_ok=True)
            parts.append(part)
            file_reports.append(report)
            download_reports.append(
                {
                    "recording_token": manifest_row["recording_token"],
                    "label": label_download,
                    "process": process_download,
                    "raw_bytes_deleted_after_preparation": True,
                }
            )
        leftovers = list(temp_root.iterdir())
        if leftovers:
            raise BenchmarkIntegrityError(f"GIW exact raw-byte cleanup failed: {leftovers}")

    prepared = assemble_exact_gaze_in_wild_benchmark(
        parts,
        file_reports,
        reference_manifest,
        execution_protocol,
    )
    result = run_exact_gaze_in_wild_model_validation(prepared, execution_protocol)
    record: dict[str, Any] = {
        "record_type": "gaze-in-wild-exact-participant-disjoint-validation-discovery-v1",
        "source_binding": {
            "reference_manifest_fingerprint_sha256": REFERENCE_MANIFEST_FINGERPRINT,
            "execution_protocol_fingerprint_sha256": EXECUTION_PROTOCOL_FINGERPRINT,
            "processdata_exact_identity_ledger_fingerprint_sha256": (
                EXPECTED_PROCESS_LEDGER_FINGERPRINT
            ),
            "frozen_figshare_metadata_source_probe_fingerprint_sha256": frozen.get(
                "source_probe_fingerprint_sha256"
            ),
            "figshare_project_id": 74580,
            "processdata_article_id": 11673645,
            "labeldata_article_id": 11673696,
        },
        "execution": {
            "selected_labeller_id": 5,
            "selected_participant_count": 12,
            "selected_recording_count": 18,
            "selected_source_sample_count": 1_590_659,
            "downloaded_pair_count": len(download_reports),
            "all_selected_label_and_process_bytes_reverified": True,
            "all_label_process_timestamp_vectors_exactly_equal": True,
            "all_raw_mat_bytes_deleted_after_preparation": True,
            "processdata_cleaned_downloaded": False,
            "processdata_cleaned_article_id": int(cleaned["id"]),
            "downloads": download_reports,
        },
        "preparation": prepared.preparation_report,
        "split_integrity": result.split_integrity,
        "benchmark_report": result.report,
        "scientific_boundary": {
            "empirical_metrics_computed": True,
            "performance_evidence_reviewed": False,
            "participant_disjoint_model_validation_executed": True,
            "participant_disjoint_model_validation_created": False,
            "task_stratified_model_validation_created": False,
            "complete_file_to_publication_task_mapping_verified": False,
            "cross_dataset_validation_created": False,
            "gp3_validity_claim_created": False,
            "quarantine_exit_authorized": False,
            "new_empirical_performance_claim_created": False,
        },
        "raw_dataset_bytes_retained": False,
    }
    record["discovery_fingerprint_sha256"] = benchmark_fingerprint(record)
    output_path.write_text(
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen", required=True, type=Path)
    parser.add_argument("--reference-manifest", required=True, type=Path)
    parser.add_argument("--execution-protocol", required=True, type=Path)
    parser.add_argument("--process-identities", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--retries", type=int, default=3)
    args = parser.parse_args()
    if args.retries < 1 or args.retries > 5:
        raise SystemExit("--retries must be between 1 and 5")
    record = run(
        frozen_path=args.frozen,
        reference_manifest_path=args.reference_manifest,
        execution_protocol_path=args.execution_protocol,
        process_identity_path=args.process_identities,
        output_path=args.output,
        retries=args.retries,
    )
    report = record["benchmark_report"]
    print("discovery_fingerprint_sha256", record["discovery_fingerprint_sha256"])
    print("benchmark_report_fingerprint_sha256", report["report_fingerprint_sha256"])
    print("analysis_rows", record["preparation"]["analysis_rows"])
    print("participant_count", record["split_integrity"]["participant_count"])
    print("fold_count", record["split_integrity"]["fold_count"])
    for row in report["metrics"]["summary"]:
        print(
            "model_summary",
            row["model"],
            "balanced_accuracy_mean",
            row["balanced_accuracy_mean"],
            "macro_f1_mean",
            row["macro_f1_mean"],
            "event_f1_mean",
            row["event_f1_mean"],
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
