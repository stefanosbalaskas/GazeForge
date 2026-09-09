from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError

EXPECTED_EVIDENCE_FINGERPRINT = (
    "2352b5969285c4d3d182035570b3a3b76461fa683e50d69cf4ff0e2f6a827aec"
)
EXPECTED_RECORD_TYPE = (
    "gaze-in-wild-perform-lab-task-structure-corroboration-evidence-v1"
)
EXPECTED_REVIEW_STATUS = "first_party_structural_corroboration_only"
EXPECTED_REPOSITORY = (
    "https://github.com/PerForm-Lab-RIT/Pupil-Labs-Core-RITnet-Plugins"
)
EXPECTED_COMMIT = "ebec5d1db118e39de60a14160f09ee33cd7f3b5d"
EXPECTED_TREE = "67af6104f7d52c969be7737b04fa349be6a2ec4f"
EXPECTED_FILE_PATH = "ritnet/Ellseg_v2/dataset_generation/ExtractedGIW.py"
EXPECTED_FILE_BLOB = "ae51e50eb9f3d224417d1fd24253052196480870"
EXPECTED_TASKS = [
    "Indoor_Walk",
    "Ball_Catch",
    "Visual_Search",
    "Tea_Making",
]
EXPECTED_OBSERVED_CONTRACT = {
    "project_description_mentions_gaze_in_the_wild": True,
    "task_list_exact": EXPECTED_TASKS,
    "processdata_directory_template": "extracted_data/<task>/ProcessData_cleaned",
    "processdata_fields_read": ["PrIdx", "TrIdx"],
    "raw_gaze_directory_template": "<path_data>/<PrIdx>/<TrIdx>/Gaze",
}
EXPECTED_BOUNDARY_KEYS = {
    "authoritative_trial_task_mapping_verified",
    "complete_trial_task_mapping_verified",
    "task_stratified_validation_authorized",
    "task_stratified_validation_created",
    "new_empirical_performance_claim_created",
    "cross_dataset_validation_created",
    "native_60hz_validity_created",
    "gp3_validity_created",
    "acquisition_hardware_cadence_verified",
    "quarantine_exit_authorized",
}


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise BenchmarkIntegrityError(message)


def validate_gaze_in_wild_perform_lab_task_structure_evidence(
    record: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate first-party GIW task-structure corroboration without promotion.

    The PerForm-Lab-RIT source is materially stronger than secondary replication
    evidence because it is first-party institutional code and its in-file metadata
    identifies ``rakshit``. It verifies task-separated extraction structure and
    ProcessData ``PrIdx``/``TrIdx`` linkage, but it does not enumerate a numeric
    ``TrIdx`` -> task lookup. The contract therefore keeps task-stratified claims
    and ``TrIdx 4 -> Tea_Making`` inference closed.
    """

    payload = dict(record)
    actual_fingerprint = payload.get("evidence_fingerprint_sha256")
    body = dict(payload)
    body.pop("evidence_fingerprint_sha256", None)

    _require(
        actual_fingerprint == _canonical_sha256(body),
        "PerForm-Lab task-structure evidence fingerprint does not match its body",
    )
    _require(
        actual_fingerprint == EXPECTED_EVIDENCE_FINGERPRINT,
        "PerForm-Lab task-structure evidence fingerprint is not reviewed identity",
    )
    _require(
        payload.get("record_type") == EXPECTED_RECORD_TYPE,
        "PerForm-Lab task-structure record type drifted",
    )
    _require(
        payload.get("dataset") == "Gaze-in-the-Wild",
        "PerForm-Lab task-structure dataset drifted",
    )
    _require(
        payload.get("review_status") == EXPECTED_REVIEW_STATUS,
        "PerForm-Lab evidence must remain structural corroboration only",
    )

    source = payload.get("source")
    _require(isinstance(source, Mapping), "PerForm-Lab source is missing")
    _require(
        source.get("classification") == "first_party_institutional_code",
        "PerForm-Lab source classification drifted",
    )
    _require(
        source.get("institutional_owner") == "PerForm-Lab-RIT",
        "PerForm-Lab institutional owner drifted",
    )
    _require(
        source.get("repository") == EXPECTED_REPOSITORY,
        "PerForm-Lab repository drifted",
    )
    _require(
        source.get("pinned_commit_sha1") == EXPECTED_COMMIT,
        "PerForm-Lab commit drifted",
    )
    _require(
        source.get("pinned_tree_sha1") == EXPECTED_TREE,
        "PerForm-Lab tree drifted",
    )

    source_file = source.get("file")
    _require(isinstance(source_file, Mapping), "PerForm-Lab source file is missing")
    _require(
        source_file.get("path") == EXPECTED_FILE_PATH,
        "PerForm-Lab source path drifted",
    )
    _require(
        source_file.get("git_blob_sha1") == EXPECTED_FILE_BLOB,
        "PerForm-Lab source blob drifted",
    )
    _require(
        source_file.get("in_file_author") == "rakshit",
        "PerForm-Lab in-file author metadata drifted",
    )
    _require(
        source_file.get("in_file_created") == "2021-02-05",
        "PerForm-Lab in-file creation metadata drifted",
    )
    _require(
        source_file.get("observed_contract") == EXPECTED_OBSERVED_CONTRACT,
        "PerForm-Lab observed extraction contract drifted",
    )

    corroboration = payload.get("first_party_structural_corroboration")
    _require(
        isinstance(corroboration, Mapping),
        "PerForm-Lab structural corroboration section is missing",
    )
    _require(
        corroboration.get("task_directory_labels") == EXPECTED_TASKS,
        "PerForm-Lab task-directory labels drifted",
    )
    _require(
        corroboration.get("task_directory_processdata_linkage_observed") is True,
        "PerForm-Lab ProcessData task-directory linkage must remain recorded",
    )
    _require(
        corroboration.get("processdata_fields_read") == ["PrIdx", "TrIdx"],
        "PerForm-Lab ProcessData field contract drifted",
    )
    _require(
        corroboration.get("raw_recording_address_uses_pridx_tridx") is True,
        "PerForm-Lab raw recording identity linkage drifted",
    )
    _require(
        corroboration.get("direct_numeric_trial_task_bindings") == [],
        "PerForm-Lab source cannot be promoted into numeric task bindings",
    )
    _require(
        corroboration.get("complete_numeric_mapping_recorded") is False,
        "PerForm-Lab source cannot record a complete numeric mapping",
    )
    _require(
        corroboration.get("trial_index_4")
        == {
            "status": "unresolved",
            "explicit_first_party_numeric_binding_found": False,
            "tea_making_inferred_by_elimination": False,
        },
        "PerForm-Lab TrIdx 4 must remain unresolved and uninferred",
    )

    boundary = payload.get("scientific_boundary")
    _require(
        isinstance(boundary, Mapping),
        "PerForm-Lab scientific boundary is missing",
    )
    _require(
        set(boundary) == EXPECTED_BOUNDARY_KEYS,
        "PerForm-Lab scientific boundary contract drifted",
    )
    _require(
        not any(bool(value) for value in boundary.values()),
        "PerForm-Lab structural corroboration cannot promote scientific gates",
    )

    claim_limit = payload.get("claim_limit")
    _require(
        isinstance(claim_limit, str)
        and "first-party institutional code corroboration" in claim_limit
        and "does not directly enumerate a numeric TrIdx-to-task lookup" in claim_limit
        and "does not explicitly bind TrIdx 4 to Tea_Making" in claim_limit,
        "PerForm-Lab claim limit drifted",
    )

    return payload


def load_gaze_in_wild_perform_lab_task_structure_evidence(
    path: str | Path,
) -> dict[str, Any]:
    """Load and validate the frozen PerForm-Lab structural evidence record."""

    record = json.loads(Path(path).read_text(encoding="utf-8"))
    _require(
        isinstance(record, Mapping),
        "PerForm-Lab task-structure evidence must be a JSON object",
    )
    return validate_gaze_in_wild_perform_lab_task_structure_evidence(record)
