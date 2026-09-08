#!/usr/bin/env python
"""Run convergence-qualified participant-disjoint validation on exact GIW bytes."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from run_gaze_in_wild_exact_participant_disjoint_validation import (
    EXPECTED_PROCESS_LEDGER_FINGERPRINT,
    _download_verified,
    _files_by_name,
    _item_by_label,
    _load_json,
    _process_sha_map,
)
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_exact_validation import (
    EXECUTION_PROTOCOL_FINGERPRINT,
    REFERENCE_MANIFEST_FINGERPRINT,
    assemble_exact_gaze_in_wild_benchmark,
    prepare_exact_gaze_in_wild_recording,
    validate_exact_execution_protocol,
    validate_exact_reference_manifest,
)
from gazeforge.gaze_in_wild_exact_validation_v2 import (
    EXECUTION_PROTOCOL_V2_FINGERPRINT,
    run_exact_gaze_in_wild_model_validation_v2,
    validate_exact_execution_protocol_v2,
)


def run(
    *,
    frozen_path: Path,
    reference_manifest_path: Path,
    preparation_protocol_path: Path,
    execution_protocol_v2_path: Path,
    process_identity_path: Path,
    output_path: Path,
    retries: int,
) -> dict[str, Any]:
    """Verify exact source pairs, prepare once, and execute the v2 model protocol."""
    frozen = _load_json(frozen_path)
    reference_manifest = validate_exact_reference_manifest(_load_json(reference_manifest_path))
    preparation_protocol = validate_exact_execution_protocol(_load_json(preparation_protocol_path))
    execution_protocol_v2 = validate_exact_execution_protocol_v2(
        _load_json(execution_protocol_v2_path)
    )
    process_sha = _process_sha_map(_load_json(process_identity_path))
    label_rows = _files_by_name(_item_by_label(frozen, "LabelData"))
    process_rows = _files_by_name(_item_by_label(frozen, "ProcessData"))
    cleaned = _item_by_label(frozen, "ProcessData_cleaned")

    selected_files = reference_manifest["selected_reference"]["files"]
    parts = []
    file_reports: list[dict[str, Any]] = []
    download_reports: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="gazeforge-giw-exact-validation-v2-") as directory:
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

            label_path = temp_root / label_name
            process_path = temp_root / process_name
            print(
                f"[GIW exact v2 {index}/18] verifying {label_name} + {process_name}",
                flush=True,
            )
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
                    preparation_protocol,
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
            raise BenchmarkIntegrityError(f"GIW exact v2 raw-byte cleanup failed: {leftovers}")

    prepared = assemble_exact_gaze_in_wild_benchmark(
        parts,
        file_reports,
        reference_manifest,
        preparation_protocol,
    )
    result = run_exact_gaze_in_wild_model_validation_v2(prepared, execution_protocol_v2)
    report_protocol = result.report["protocol"]
    if report_protocol.get("contextmlp_convergence_warning_count") != 0:
        raise BenchmarkIntegrityError("GIW exact v2 retained a ContextMLP convergence warning.")
    if report_protocol.get("contextmlp_convergence_requirement_satisfied") is not True:
        raise BenchmarkIntegrityError("GIW exact v2 convergence requirement was not satisfied.")

    record: dict[str, Any] = {
        "record_type": "gaze-in-wild-exact-participant-disjoint-validation-discovery-v2",
        "source_binding": {
            "reference_manifest_fingerprint_sha256": REFERENCE_MANIFEST_FINGERPRINT,
            "preparation_protocol_v1_fingerprint_sha256": EXECUTION_PROTOCOL_FINGERPRINT,
            "execution_protocol_v2_fingerprint_sha256": EXECUTION_PROTOCOL_V2_FINGERPRINT,
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
            "contextmlp_convergence_warning_count": 0,
            "contextmlp_convergence_requirement_satisfied": True,
            "downloads": download_reports,
        },
        "preparation": prepared.preparation_report,
        "split_integrity": result.split_integrity,
        "benchmark_report": result.report,
        "scientific_boundary": {
            "empirical_metrics_computed": True,
            "participant_disjoint_model_validation_executed": True,
            "contextmlp_convergence_requirement_satisfied": True,
            "performance_evidence_reviewed": False,
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
    parser.add_argument("--preparation-protocol", required=True, type=Path)
    parser.add_argument("--execution-protocol-v2", required=True, type=Path)
    parser.add_argument("--process-identities", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--retries", type=int, default=3)
    args = parser.parse_args()
    if args.retries < 1 or args.retries > 5:
        raise SystemExit("--retries must be between 1 and 5")
    record = run(
        frozen_path=args.frozen,
        reference_manifest_path=args.reference_manifest,
        preparation_protocol_path=args.preparation_protocol,
        execution_protocol_v2_path=args.execution_protocol_v2,
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
    print("contextmlp_convergence_warning_count", 0)
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
