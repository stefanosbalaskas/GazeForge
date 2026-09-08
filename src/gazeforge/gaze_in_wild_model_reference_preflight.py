"""Pre-register a human reference stream for exact-distribution GIW validation."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .exceptions import BenchmarkIntegrityError

FEASIBILITY_RECORD_TYPE = "gaze-in-wild-labeldata-hha-feasibility-probe-v1"
PREFLIGHT_RECORD_TYPE = "gaze-in-wild-exact-model-reference-preflight-v1"
EXPECTED_FILE_COUNT = 50
EXPECTED_TOTAL_BYTES = 28_725_824
EXPECTED_LABELDATA_ARTICLE_ID = 11673696
EXPECTED_EXACT_BYTE_EVIDENCE = (
    "dbf277d698266fe53e337a15fc342e9af1835460d2bcc69c3992635de8fa0a00"
)
SELECTION_POLICY = (
    "maximize_distinct_participants_then_distinct_recordings_then_lowest_labeller_id"
)
_FILENAME_RE = re.compile(
    r"^PrIdx_(?P<participant>\d+)_TrIdx_(?P<trial>\d+)_Lbr_(?P<labeller>\d+)\.mat$"
)
_TOKEN_RE = re.compile(r"^PrIdx_(\d+)_TrIdx_(\d+)$")
_ALLOWED_LABEL_CODES = frozenset(range(6))


@dataclass(frozen=True, slots=True)
class GazeInWildModelReferencePreflight:
    """Deterministic source-only reference selection for the exact GIW distribution."""

    selected_labeller_id: int
    selected_participant_count: int
    selected_recording_count: int
    selected_file_count: int
    selected_observed_label_codes: tuple[int, ...]
    stable_source_manifest_sha256: str
    preflight_fingerprint_sha256: str


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(f"GIW model-reference {label} must be an object.")
    return value


def _require(value: Any, expected: Any, label: str) -> None:
    if value != expected:
        raise BenchmarkIntegrityError(f"GIW model-reference {label} drifted.")


def _stable_source_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "figshare_file_id": row.get("figshare_file_id"),
        "name": row.get("name"),
        "size_bytes": row.get("size_bytes"),
        "md5": row.get("md5"),
        "sha256": row.get("sha256"),
        "participant_token": row.get("participant_token"),
        "trial_token": row.get("trial_token"),
        "recording_token": row.get("recording_token"),
        "labeller_id": row.get("labeller_id"),
        "process_filename": row.get("process_filename"),
        "n_samples": row.get("n_samples"),
        "timestamp_sha256_float64_le": row.get("timestamp_sha256_float64_le"),
        "labels_sha256_int64_le": row.get("labels_sha256_int64_le"),
        "inferred_sampling_rate_hz": row.get("inferred_sampling_rate_hz"),
        "label_code_counts": row.get("label_code_counts"),
        "filename_struct_labeller_agree": row.get("filename_struct_labeller_agree"),
        "raw_bytes_retained": row.get("raw_bytes_retained"),
    }


def _validated_rows(feasibility: Mapping[str, Any]) -> list[dict[str, Any]]:
    _require(feasibility.get("record_type"), FEASIBILITY_RECORD_TYPE, "record type")
    source = _mapping(feasibility.get("source_binding"), "source binding")
    _require(source.get("labeldata_article_id"), EXPECTED_LABELDATA_ARTICLE_ID, "article id")
    _require(
        source.get("exact_byte_reviewed_evidence_fingerprint_sha256"),
        EXPECTED_EXACT_BYTE_EVIDENCE,
        "exact-byte evidence binding",
    )
    verified = _mapping(feasibility.get("verified_labeldata"), "verified LabelData")
    _require(verified.get("file_count"), EXPECTED_FILE_COUNT, "file count")
    _require(verified.get("total_size_bytes"), EXPECTED_TOTAL_BYTES, "total bytes")
    for key in (
        "all_files_matched_frozen_size_and_md5",
        "all_files_resolve_to_frozen_original_processdata",
        "all_raw_mat_bytes_deleted_after_inspection",
    ):
        _require(verified.get(key), True, key)
    boundary = _mapping(feasibility.get("scientific_boundary"), "scientific boundary")
    _require(boundary.get("exact_labeldata_bytes_reverified"), True, "exact-byte reverification")
    for key in (
        "participant_disjoint_model_validation_created",
        "cross_dataset_validation_created",
        "gp3_validity_claim_created",
        "complete_file_to_publication_task_mapping_verified",
        "quarantine_exit_authorized",
        "new_empirical_performance_claim_created",
    ):
        _require(boundary.get(key), False, key)
    _require(feasibility.get("raw_dataset_bytes_retained"), False, "raw-byte retention")

    raw_rows = verified.get("files")
    if not isinstance(raw_rows, list) or len(raw_rows) != EXPECTED_FILE_COUNT:
        raise BenchmarkIntegrityError("GIW model-reference requires exactly 50 file rows.")

    result: list[dict[str, Any]] = []
    names: set[str] = set()
    ids: set[int] = set()
    for value in raw_rows:
        row = dict(_mapping(value, "file row"))
        name = row.get("name")
        if not isinstance(name, str):
            raise BenchmarkIntegrityError("GIW model-reference file name is missing.")
        match = _FILENAME_RE.fullmatch(name)
        if match is None or name in names:
            raise BenchmarkIntegrityError("GIW model-reference filename grammar/uniqueness drifted.")
        participant = int(match.group("participant"))
        trial = int(match.group("trial"))
        labeller = int(match.group("labeller"))
        file_id = row.get("figshare_file_id")
        if not isinstance(file_id, int) or file_id in ids:
            raise BenchmarkIntegrityError("GIW model-reference Figshare file id drifted.")
        names.add(name)
        ids.add(file_id)
        _require(row.get("participant_token"), f"PrIdx_{participant}", f"{name} participant")
        _require(row.get("trial_token"), f"TrIdx_{trial}", f"{name} trial")
        _require(
            row.get("recording_token"),
            f"PrIdx_{participant}_TrIdx_{trial}",
            f"{name} recording",
        )
        _require(row.get("labeller_id"), labeller, f"{name} labeller")
        _require(row.get("process_filename"), f"PrIdx_{participant}_TrIdx_{trial}.mat", f"{name} process")
        _require(row.get("filename_struct_labeller_agree"), True, f"{name} LbrIdx agreement")
        _require(row.get("raw_bytes_retained"), False, f"{name} raw-byte retention")
        sample_count = row.get("n_samples")
        if not isinstance(sample_count, int) or sample_count < 2:
            raise BenchmarkIntegrityError(f"GIW model-reference {name} sample count is invalid.")
        rate = row.get("inferred_sampling_rate_hz")
        if not isinstance(rate, (int, float)) or not 250.0 < float(rate) < 350.0:
            raise BenchmarkIntegrityError(f"GIW model-reference {name} processed rate is invalid.")
        counts = row.get("label_code_counts")
        if not isinstance(counts, Mapping) or not counts:
            raise BenchmarkIntegrityError(f"GIW model-reference {name} label counts are missing.")
        observed_codes: set[int] = set()
        observed_total = 0
        for code_text, count in counts.items():
            try:
                code = int(code_text)
            except (TypeError, ValueError) as exc:
                raise BenchmarkIntegrityError(
                    f"GIW model-reference {name} contains a malformed label code."
                ) from exc
            if code not in _ALLOWED_LABEL_CODES or not isinstance(count, int) or count < 0:
                raise BenchmarkIntegrityError(
                    f"GIW model-reference {name} contains an unsupported label count."
                )
            observed_codes.add(code)
            observed_total += count
        if observed_total != sample_count:
            raise BenchmarkIntegrityError(
                f"GIW model-reference {name} label counts do not sum to n_samples."
            )
        row["_observed_codes"] = observed_codes
        result.append(row)
    return result


def build_gaze_in_wild_model_reference_preflight(
    feasibility: Mapping[str, Any],
) -> tuple[dict[str, Any], GazeInWildModelReferencePreflight]:
    """Select one exact-distribution human reference using source coverage only."""

    rows = _validated_rows(feasibility)
    by_labeller: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_labeller[int(row["labeller_id"])].append(row)

    candidates: list[dict[str, Any]] = []
    for labeller in sorted(by_labeller):
        members = by_labeller[labeller]
        participants = sorted({str(row["participant_token"]) for row in members})
        recordings = sorted({str(row["recording_token"]) for row in members})
        observed_codes = sorted(
            {code for row in members for code in row["_observed_codes"]}
        )
        aggregate_counts: Counter[int] = Counter()
        for row in members:
            aggregate_counts.update(
                {int(code): int(count) for code, count in row["label_code_counts"].items()}
            )
        candidates.append(
            {
                "labeller_id": labeller,
                "participant_count": len(participants),
                "recording_count": len(recordings),
                "file_count": len(members),
                "participants": participants,
                "recordings": recordings,
                "observed_label_codes": observed_codes,
                "label_code_counts": {
                    str(code): aggregate_counts[code] for code in sorted(aggregate_counts)
                },
                "total_samples": sum(int(row["n_samples"]) for row in members),
            }
        )
    if not candidates:
        raise BenchmarkIntegrityError("GIW model-reference has no candidate labellers.")

    ranked = sorted(
        candidates,
        key=lambda row: (
            -int(row["participant_count"]),
            -int(row["recording_count"]),
            int(row["labeller_id"]),
        ),
    )
    selected = ranked[0]
    nonzero_codes = [code for code in selected["observed_label_codes"] if int(code) != 0]
    if len(nonzero_codes) < 2:
        raise BenchmarkIntegrityError(
            "GIW model-reference selected stream has fewer than two labelled event classes."
        )
    if int(selected["participant_count"]) < 2:
        raise BenchmarkIntegrityError(
            "GIW model-reference selected stream has fewer than two participants."
        )

    selected_rows = [
        row for row in rows if int(row["labeller_id"]) == int(selected["labeller_id"])
    ]
    source_manifest = [_stable_source_row(row) for row in selected_rows]
    stable_manifest = _sha(source_manifest)
    record: dict[str, Any] = {
        "record_type": PREFLIGHT_RECORD_TYPE,
        "selection_policy": {
            "name": SELECTION_POLICY,
            "uses_participant_coverage": True,
            "uses_recording_coverage_as_tiebreak": True,
            "uses_lowest_labeller_id_as_final_tiebreak": True,
            "uses_label_frequencies_for_selection": False,
            "uses_model_performance_for_selection": False,
            "policy_locked_before_model_execution": True,
        },
        "source_binding": {
            "figshare_project_id": 74580,
            "labeldata_article_id": EXPECTED_LABELDATA_ARTICLE_ID,
            "exact_byte_reviewed_evidence_fingerprint_sha256": EXPECTED_EXACT_BYTE_EVIDENCE,
            "labeldata_feasibility_probe_fingerprint_sha256": feasibility.get(
                "probe_fingerprint_sha256"
            ),
            "selected_reference_stable_source_manifest_sha256": stable_manifest,
        },
        "candidate_labellers": candidates,
        "selected_reference": {
            **selected,
            "nonzero_observed_label_codes": nonzero_codes,
            "files": source_manifest,
        },
        "model_protocol_preregistration": {
            "task_mapping_used": False,
            "task_stratified_validation_authorized": False,
            "participant_group_key": "PrIdx distribution-native participant token",
            "trial_key": "TrIdx distribution-native opaque trial token",
            "analysis_sampling_rate_hz": 60.0,
            "sampling_origin": "derived_downsampled_from_exact_processed_timestamp_grids",
            "min_label_purity": 0.75,
            "excluded_event_labels": ["ambiguous", "unlabelled", "undefined"],
            "max_coordinate_gap_factor": 1.5,
            "n_splits": 5,
            "models": ["I-VT", "RandomForest", "ContextMLP"],
            "ivt_velocity_threshold_px_s": 1000.0,
            "min_confidence": 0.0,
            "random_state": 42,
            "random_forest_n_estimators": 200,
            "context_radius_ms": 50.0,
            "rolling_window_ms": 80.0,
            "hidden_layer_sizes": [64, 32],
            "temporal_solver": "adam",
            "temporal_max_iter": 200,
            "calibration_bins": 10,
            "event_min_iou": 0.5,
            "event_class_sensitivity_from_fixed_oof_predictions": True,
            "models_refit_by_event_class": False,
        },
        "scientific_boundary": {
            "reference_labeller_preregistered": True,
            "exact_distribution_model_execution_authorized": True,
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
    record["preflight_fingerprint_sha256"] = _sha(record)
    result = GazeInWildModelReferencePreflight(
        selected_labeller_id=int(selected["labeller_id"]),
        selected_participant_count=int(selected["participant_count"]),
        selected_recording_count=int(selected["recording_count"]),
        selected_file_count=int(selected["file_count"]),
        selected_observed_label_codes=tuple(int(value) for value in selected["observed_label_codes"]),
        stable_source_manifest_sha256=stable_manifest,
        preflight_fingerprint_sha256=record["preflight_fingerprint_sha256"],
    )
    return record, result
