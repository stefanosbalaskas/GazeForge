"""Explicit structural screening for quarantined Gaze-in-the-Wild recovery candidates.

The generic recovery review deliberately leaves every file role unclassified and forbids
MATLAB-schema inference. This module adds a separate, opt-in layer: an operator explicitly
selects one already-inventoried file and asks whether that exact file is structurally
compatible with GazeForge's ProcessData-side adapter. A successful screen never changes
source authority, rights, quarantine status, source-audit readiness, or empirical eligibility.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .benchmarks import benchmark_fingerprint
from .exceptions import BenchmarkIntegrityError
from .gaze_in_wild_processdata_preflight import preflight_gaze_in_wild_processdata
from .gaze_in_wild_recovery import (
    recovery_candidate_record_fingerprint,
    validate_gaze_in_wild_recovery_candidate_review,
    verify_gaze_in_wild_recovery_candidate_tree,
)

RECORD_TYPE = "gaze-in-wild-recovery-candidate-processdata-screen-v1"
CANDIDATE_STATUS = "quarantined"

_SCREENING_POLICY = {
    "selected_path_was_explicit": True,
    "generic_recovery_file_roles_remain_unclassified": True,
    "filename_identity_inference_permitted": False,
    "source_authority_inference_permitted": False,
    "rights_inference_permitted": False,
    "selected_file_structure_can_establish_distribution_identity": False,
    "selected_file_structure_can_authorize_quarantine_exit": False,
    "candidate_can_materialize_empirical_audit_spec": False,
}

_SCIENTIFIC_BOUNDARY = {
    "candidate_tree_binding_verified": True,
    "selected_processdata_structure_compatible": True,
    "source_authority_verified": False,
    "exact_original_distribution_format_verified": False,
    "exact_original_copy_identity_verified": False,
    "dataset_file_rights_resolved": False,
    "analysis_use_authorized": False,
    "redistribution_authorized": False,
    "participant_mapping_verified": False,
    "complete_trial_task_mapping_verified": False,
    "coordinate_unit_verified_from_candidate": False,
    "sampling_cadence_verified_from_candidate": False,
    "corpus_sampling_rate_distribution_verified": False,
    "published_acquisition_cadence_verified_from_candidate": False,
    "separate_labeldata_recovered": False,
    "independent_labeller_recoverability_verified": False,
    "quarantine_exit_authorized": False,
    "source_audit_ready": False,
    "empirical_evidence_eligible": False,
    "human_human_agreement_created": False,
    "participant_disjoint_model_validation_created": False,
    "cross_dataset_performance_created": False,
    "gp3_validity_created": False,
    "frozen_evidence_performance_claim_created": False,
}

CLAIM_LIMIT = (
    "This record proves only that one explicitly selected file from one exact quarantined "
    "candidate tree passes the ProcessData structural preflight. It does not infer the file's "
    "historical filename role, source authority, original-distribution identity, dataset-file "
    "rights, participant/task/labeller identity, coordinate semantics, acquisition cadence, "
    "quarantine-exit authorization, source-audit readiness, or empirical eligibility."
)


def candidate_processdata_screen_fingerprint(record: Mapping[str, Any]) -> str:
    """Return the canonical screen fingerprint excluding the stored value."""
    body = dict(record)
    body.pop("record_fingerprint_sha256", None)
    return benchmark_fingerprint(body)


def _load_json_object(
    value: Mapping[str, Any] | str | Path,
    *,
    label: str,
) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    path = Path(value)
    if not path.is_file():
        raise FileNotFoundError(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(f"{label} must be valid UTF-8 JSON.") from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(f"{label} must contain one JSON object.")
    return payload


def _safe_relative_path(value: str | Path) -> str:
    raw = str(value).replace("\\", "/").strip()
    path = Path(raw)
    if not raw or path.is_absolute() or raw.startswith("/") or ".." in path.parts:
        raise BenchmarkIntegrityError(
            "GIW candidate ProcessData screen requires one safe explicit relative path."
        )
    normalized = path.as_posix()
    if normalized in {"", "."}:
        raise BenchmarkIntegrityError(
            "GIW candidate ProcessData screen requires one safe explicit relative path."
        )
    return normalized


def _inventory_file(recovery: Mapping[str, Any], relative_path: str) -> dict[str, Any]:
    inventory = recovery.get("inventory")
    if not isinstance(inventory, Mapping):
        raise BenchmarkIntegrityError("GIW recovery review inventory is missing.")
    files = inventory.get("files")
    if not isinstance(files, list):
        raise BenchmarkIntegrityError("GIW recovery review file manifest is missing.")
    matches = [
        item
        for item in files
        if isinstance(item, Mapping) and str(item.get("path", "")) == relative_path
    ]
    if len(matches) != 1:
        raise BenchmarkIntegrityError(
            "Explicit GIW ProcessData screen path must identify exactly one reviewed inventory file."
        )
    item = matches[0]
    if item.get("role") != "unclassified":
        raise BenchmarkIntegrityError(
            "GIW candidate ProcessData screening cannot promote generic recovery file roles."
        )
    return {
        "relative_path": relative_path,
        "sha256": str(item["sha256"]),
        "bytes": int(item["bytes"]),
        "generic_recovery_role": "unclassified",
    }


def _recovery_binding(recovery: Mapping[str, Any]) -> dict[str, Any]:
    inventory = recovery.get("inventory")
    if not isinstance(inventory, Mapping):
        raise BenchmarkIntegrityError("GIW recovery review inventory is missing.")
    return {
        "candidate_kind": str(recovery["candidate_kind"]),
        "recovery_record_fingerprint_sha256": recovery_candidate_record_fingerprint(recovery),
        "recovery_tree_fingerprint_sha256": str(inventory["tree_fingerprint_sha256"]),
    }


def build_gaze_in_wild_candidate_processdata_screen(
    root: str | Path,
    recovery_record_or_path: Mapping[str, Any] | str | Path,
    *,
    processdata_relative_path: str | Path,
) -> dict[str, Any]:
    """Screen one explicitly selected candidate file while keeping the tree quarantined.

    The recovery review is validated and the full tree is re-inventoried before the selected
    file is opened. The selected file's current bytes are bound to its reviewed inventory
    hash/size and then passed to :func:`preflight_gaze_in_wild_processdata`.
    """
    recovery = _load_json_object(
        recovery_record_or_path,
        label="Gaze-in-the-Wild recovery candidate review",
    )
    validate_gaze_in_wild_recovery_candidate_review(recovery)
    verified = verify_gaze_in_wild_recovery_candidate_tree(root, recovery)

    relative_path = _safe_relative_path(processdata_relative_path)
    selected = _inventory_file(recovery, relative_path)
    root_path = Path(root).resolve()
    candidate_file = (root_path / relative_path).resolve()
    if root_path not in candidate_file.parents:
        raise BenchmarkIntegrityError(
            "GIW candidate ProcessData screen path escapes the reviewed candidate tree."
        )
    if not candidate_file.is_file():
        raise BenchmarkIntegrityError(
            "Explicit GIW ProcessData screen path is not a current candidate file."
        )

    preflight = preflight_gaze_in_wild_processdata(
        candidate_file,
        expected_sha256=selected["sha256"],
        expected_bytes=selected["bytes"],
    )
    processdata = preflight.to_dict()
    processdata["path"] = relative_path

    binding = _recovery_binding(recovery)
    if binding["recovery_record_fingerprint_sha256"] != verified.record_fingerprint_sha256:
        raise BenchmarkIntegrityError("GIW recovery record fingerprint binding drifted.")
    if binding["recovery_tree_fingerprint_sha256"] != verified.tree_fingerprint_sha256:
        raise BenchmarkIntegrityError("GIW recovery tree fingerprint binding drifted.")

    record: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "candidate_status": CANDIDATE_STATUS,
        "dataset": "Gaze-in-the-Wild",
        **binding,
        "selected_file": selected,
        "processdata_preflight": processdata,
        "screening_policy": dict(_SCREENING_POLICY),
        "scientific_boundary": dict(_SCIENTIFIC_BOUNDARY),
        "claim_limit": CLAIM_LIMIT,
    }
    record["record_fingerprint_sha256"] = candidate_processdata_screen_fingerprint(record)
    return record


def validate_gaze_in_wild_candidate_processdata_screen(
    record_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Validate a candidate screen without granting authority, rights, or exit status."""
    record = _load_json_object(
        record_or_path,
        label="Gaze-in-the-Wild candidate ProcessData screen",
    )
    if record.get("record_type") != RECORD_TYPE:
        raise BenchmarkIntegrityError("GIW candidate ProcessData screen record_type drifted.")
    if record.get("candidate_status") != CANDIDATE_STATUS:
        raise BenchmarkIntegrityError("GIW candidate ProcessData screen must remain quarantined.")
    if record.get("dataset") != "Gaze-in-the-Wild":
        raise BenchmarkIntegrityError("GIW candidate ProcessData screen dataset identity drifted.")

    for key in (
        "recovery_record_fingerprint_sha256",
        "recovery_tree_fingerprint_sha256",
    ):
        value = str(record.get(key, ""))
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise BenchmarkIntegrityError(f"GIW candidate ProcessData screen {key} is invalid.")

    selected = record.get("selected_file")
    if not isinstance(selected, Mapping):
        raise BenchmarkIntegrityError("GIW candidate ProcessData screen selected_file is missing.")
    relative_path = _safe_relative_path(str(selected.get("relative_path", "")))
    if selected.get("relative_path") != relative_path:
        raise BenchmarkIntegrityError("GIW candidate ProcessData screen path is not normalized.")
    digest = str(selected.get("sha256", ""))
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise BenchmarkIntegrityError("GIW candidate ProcessData selected-file SHA-256 is invalid.")
    if not isinstance(selected.get("bytes"), int) or int(selected["bytes"]) < 0:
        raise BenchmarkIntegrityError("GIW candidate ProcessData selected-file byte size is invalid.")
    if selected.get("generic_recovery_role") != "unclassified":
        raise BenchmarkIntegrityError(
            "GIW candidate ProcessData screen cannot promote the generic recovery file role."
        )

    preflight = record.get("processdata_preflight")
    if not isinstance(preflight, Mapping):
        raise BenchmarkIntegrityError("GIW candidate ProcessData preflight observation is missing.")
    if preflight.get("path") != relative_path:
        raise BenchmarkIntegrityError("GIW candidate ProcessData preflight path binding drifted.")
    if preflight.get("sha256") != digest:
        raise BenchmarkIntegrityError("GIW candidate ProcessData preflight SHA-256 binding drifted.")
    if preflight.get("bytes") != selected.get("bytes"):
        raise BenchmarkIntegrityError("GIW candidate ProcessData preflight byte binding drifted.")
    if preflight.get("adapter_coordinate_fields_compatible") is not True:
        raise BenchmarkIntegrityError(
            "GIW candidate ProcessData screen requires explicit structural compatibility."
        )
    if preflight.get("timestamp_grid_valid") is not True:
        raise BenchmarkIntegrityError(
            "GIW candidate ProcessData screen requires an explicitly valid timestamp grid."
        )

    if record.get("screening_policy") != _SCREENING_POLICY:
        raise BenchmarkIntegrityError(
            "GIW candidate ProcessData screening policy cannot be promoted."
        )
    if record.get("scientific_boundary") != _SCIENTIFIC_BOUNDARY:
        raise BenchmarkIntegrityError(
            "GIW candidate ProcessData scientific boundary cannot be promoted."
        )
    if record.get("claim_limit") != CLAIM_LIMIT:
        raise BenchmarkIntegrityError("GIW candidate ProcessData claim limit drifted.")

    stored = str(record.get("record_fingerprint_sha256", ""))
    observed = candidate_processdata_screen_fingerprint(record)
    if stored != observed:
        raise BenchmarkIntegrityError("GIW candidate ProcessData screen fingerprint drifted.")
    return record


def verify_gaze_in_wild_candidate_processdata_screen(
    root: str | Path,
    recovery_record_or_path: Mapping[str, Any] | str | Path,
    screen_record_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Re-run the explicit screen and require exact equality with the reviewed record."""
    expected = validate_gaze_in_wild_candidate_processdata_screen(screen_record_or_path)
    recovery = _load_json_object(
        recovery_record_or_path,
        label="Gaze-in-the-Wild recovery candidate review",
    )
    if expected["recovery_record_fingerprint_sha256"] != recovery_candidate_record_fingerprint(
        recovery
    ):
        raise BenchmarkIntegrityError(
            "GIW candidate ProcessData screen is bound to a different recovery review."
        )
    rebuilt = build_gaze_in_wild_candidate_processdata_screen(
        root,
        recovery,
        processdata_relative_path=expected["selected_file"]["relative_path"],
    )
    if rebuilt != expected:
        raise BenchmarkIntegrityError(
            "GIW candidate ProcessData screen no longer matches the reviewed candidate tree."
        )
    return expected


def write_gaze_in_wild_candidate_processdata_screen(
    record: Mapping[str, Any],
    path: str | Path,
    *,
    candidate_root: str | Path,
    recovery_record_or_path: Mapping[str, Any] | str | Path,
    overwrite: bool = False,
) -> Path:
    """Write one reverified screen outside the quarantined candidate tree."""
    verify_gaze_in_wild_candidate_processdata_screen(
        candidate_root,
        recovery_record_or_path,
        record,
    )
    root = Path(candidate_root).resolve()
    target = Path(path)
    resolved_target = target.resolve(strict=False)
    if resolved_target == root or root in resolved_target.parents:
        raise BenchmarkIntegrityError(
            "GIW candidate ProcessData screen output must be outside the candidate tree."
        )
    if target.exists() and not overwrite:
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(dict(record), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return target
