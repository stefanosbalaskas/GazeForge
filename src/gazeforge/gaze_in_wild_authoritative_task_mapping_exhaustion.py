from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError

EXPECTED_EVIDENCE_FINGERPRINT = (
    "c0e8e0da36d329d6445dace1a56646b89c9df5f4f406761311d588eddaf36aa7"
)
EXPECTED_RECORD_TYPE = (
    "gaze-in-wild-authoritative-task-mapping-exhaustion-evidence-v1"
)
EXPECTED_REVIEW_STATUS = "scoped_authoritative_search_exhaustion_unresolved"

EXPECTED_UPSTREAM_EVIDENCE = [
    {
        "path": (
            "validation/evidence/gaze-in-wild/"
            "gaze-in-wild-task-identity-source-recovery-evidence-v1.json"
        ),
        "fingerprint_field": "evidence_fingerprint_sha256",
        "fingerprint_sha256": (
            "caac3aebc99be005f8c2dcf431041e1d727b9ca07f2e4509c06d40b4f3452212"
        ),
        "role": "pinned_first_party_git_history_and_appdesigner_search",
    },
    {
        "path": (
            "validation/evidence/gaze-in-wild/"
            "gaze-in-wild-historical-tree-recovery-evidence-v1.json"
        ),
        "fingerprint_field": "evidence_fingerprint_sha256",
        "fingerprint_sha256": (
            "f144f5b7edcdbd02e85b53e751812c41b6567105219fbfb63c097bcefc5c9ffc"
        ),
        "role": "reachable_first_party_historical_tree_recovery",
    },
    {
        "path": (
            "validation/evidence/gaze-in-wild/"
            "gaze-in-wild-supplementary-identity-evidence-v1.json"
        ),
        "fingerprint_field": "evidence_fingerprint_sha256",
        "fingerprint_sha256": (
            "a84d64342b6001adb4a2b5893db0da5ae997f6a9067d22f8cb8c72c5dcaf4db3"
        ),
        "role": "publication_supplement_task_names_without_numeric_lookup",
    },
    {
        "path": (
            "validation/evidence/gaze-in-wild/"
            "gaze-in-wild-figshare-public-metadata-summary-v1.json"
        ),
        "fingerprint_field": "summary_fingerprint_sha256",
        "fingerprint_sha256": (
            "32b14b0daf4d73204fc52b1da2205d634097a934c51746798b4c2205e620389d"
        ),
        "role": "authoritative_public_distribution_metadata_without_task_lookup",
    },
    {
        "path": (
            "validation/evidence/gaze-in-wild/"
            "gaze-in-wild-perform-lab-task-structure-corroboration-evidence-v1.json"
        ),
        "fingerprint_field": "evidence_fingerprint_sha256",
        "fingerprint_sha256": (
            "2352b5969285c4d3d182035570b3a3b76461fa683e50d69cf4ff0e2f6a827aec"
        ),
        "role": (
            "first_party_institutional_task_directory_and_pridx_tridx_"
            "structural_corroboration"
        ),
    },
    {
        "path": (
            "validation/evidence/gaze-in-wild/"
            "gaze-in-wild-ace-dnv-task-mapping-corroboration-evidence-v1.json"
        ),
        "fingerprint_field": "evidence_fingerprint_sha256",
        "fingerprint_sha256": (
            "e16aa3eea5c354ae0c6cb159cb3bdcaede19dfa535fdf23798f9fae3d35154b5"
        ),
        "role": "secondary_partial_numeric_corroboration_only",
    },
]

EXPECTED_TASKS = ["Indoor_Walk", "Ball_Catch", "Visual_Search", "Tea_Making"]
EXPECTED_SECONDARY = [
    {"trial_index": 1, "task_label": "Indoor_Walk", "status": "secondary_only"},
    {"trial_index": 2, "task_label": "Ball_Catch", "status": "secondary_only"},
    {"trial_index": 3, "task_label": "Visual_Search", "status": "secondary_only"},
]
EXPECTED_BOUNDARY_KEYS = {
    "authoritative_trial_task_mapping_verified",
    "complete_trial_task_mapping_verified",
    "tridx4_tea_making_verified",
    "task_stratified_validation_authorized",
    "task_stratified_validation_created",
    "new_empirical_performance_claim_created",
    "cross_dataset_validation_created",
    "native_60hz_validity_created",
    "gp3_validity_created",
    "acquisition_hardware_cadence_verified",
    "quarantine_exit_authorized",
    "raw_data_retention_claim_created",
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


def _mapping(record: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = record.get(key)
    _require(isinstance(value, Mapping), f"{key} must be an object")
    return value


def validate_gaze_in_wild_authoritative_task_mapping_exhaustion_evidence(
    record: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the scoped GIW authoritative-task-mapping exhaustion record.

    This validator deliberately freezes an unresolved result. Search exhaustion
    within enumerated sources cannot be converted into a numeric mapping, and
    secondary ACE-DNV corroboration cannot be promoted to first-party authority.
    """

    payload = dict(record)
    observed = payload.get("evidence_fingerprint_sha256")
    body = dict(payload)
    body.pop("evidence_fingerprint_sha256", None)
    recomputed = _canonical_sha256(body)

    _require(
        observed == recomputed,
        "GIW task-mapping exhaustion evidence fingerprint does not match its body",
    )
    _require(
        observed == EXPECTED_EVIDENCE_FINGERPRINT,
        "GIW task-mapping exhaustion evidence is not the reviewed identity",
    )
    _require(
        payload.get("record_type") == EXPECTED_RECORD_TYPE,
        "GIW task-mapping exhaustion record type drifted",
    )
    _require(
        payload.get("dataset") == "Gaze-in-the-Wild",
        "GIW task-mapping exhaustion dataset drifted",
    )
    _require(
        payload.get("review_status") == EXPECTED_REVIEW_STATUS,
        "GIW task-mapping exhaustion review status drifted",
    )
    _require(
        payload.get("upstream_evidence") == EXPECTED_UPSTREAM_EVIDENCE,
        "GIW task-mapping exhaustion upstream evidence binding drifted",
    )

    scope = _mapping(payload, "authoritative_search_scope")
    original = _mapping(scope, "original_giw_repository")
    _require(
        original
        == {
            "repository": "https://github.com/RSKothari/Gaze-in-Wild",
            "pinned_commit_sha1": "52262d44e366a53369e10ca73c5f41daf0e8f1e5",
            "reachable_commit_count": 56,
            "explicit_numeric_task_lookup_recovered": False,
            "appdesigner_container_reviewed": True,
            "publication_order_used_as_numeric_mapping": False,
        },
        "Original GIW repository exhaustion scope drifted",
    )

    published = _mapping(scope, "published_supplement_and_distribution_metadata")
    _require(
        published.get("publication_doi") == "10.1038/s41598-020-59251-5",
        "GIW publication DOI drifted",
    )
    _require(
        published.get("published_task_columns")
        == ["Indoor navigation", "Ball catching", "Visual search", "Tea making"],
        "Published GIW task columns drifted",
    )
    _require(
        published.get("explicit_numeric_task_lookup_recovered") is False,
        "Published supplement/metadata cannot be promoted to numeric task mapping",
    )
    _require(
        published.get("task_column_order_used_as_numeric_mapping") is False,
        "Publication task order cannot be used as numeric mapping",
    )

    perform = _mapping(scope, "perform_lab_institutional_repository")
    _require(
        perform.get("repository")
        == "https://github.com/PerForm-Lab-RIT/Pupil-Labs-Core-RITnet-Plugins",
        "PerForm-Lab repository drifted",
    )
    _require(
        perform.get("file_path")
        == "ritnet/Ellseg_v2/dataset_generation/ExtractedGIW.py",
        "PerForm-Lab GIW extraction path drifted",
    )
    _require(
        perform.get("pinned_commit_sha1")
        == "ebec5d1db118e39de60a14160f09ee33cd7f3b5d",
        "PerForm-Lab GIW extraction commit drifted",
    )
    _require(
        perform.get("pinned_tree_sha1")
        == "67af6104f7d52c969be7737b04fa349be6a2ec4f",
        "PerForm-Lab GIW extraction tree drifted",
    )
    _require(
        perform.get("file_git_blob_sha1")
        == "ae51e50eb9f3d224417d1fd24253052196480870",
        "PerForm-Lab GIW extraction blob drifted",
    )
    _require(
        perform.get("file_history_commit_count") == 1
        and perform.get("file_history_commit_shas")
        == ["ebec5d1db118e39de60a14160f09ee33cd7f3b5d"],
        "PerForm-Lab GIW extraction file history drifted",
    )
    _require(
        perform.get("task_directory_labels") == EXPECTED_TASKS,
        "PerForm-Lab task directory labels drifted",
    )
    _require(
        perform.get("processdata_fields_read") == ["PrIdx", "TrIdx"],
        "PerForm-Lab ProcessData field contract drifted",
    )
    _require(
        perform.get("separate_giw_mapping_manifest_found") is False,
        "A GIW mapping manifest cannot be asserted in the reviewed PerForm tree",
    )
    _require(
        perform.get("explicit_numeric_task_lookup_recovered") is False,
        "PerForm structure cannot be promoted to a numeric task lookup",
    )
    _require(
        perform.get("task_directory_order_used_as_numeric_mapping") is False,
        "PerForm task-directory order cannot be used as numeric mapping",
    )

    author_pass = _mapping(scope, "author_owned_repository_targeted_pass")
    _require(
        author_pass.get("classification") == "research_log_not_authoritative_evidence",
        "Author-repository search log classification drifted",
    )
    _require(
        author_pass.get("new_explicit_numeric_task_lookup_recovered") is False,
        "Author-repository targeted pass cannot assert a recovered lookup",
    )

    public_pass = _mapping(scope, "public_targeted_search_pass")
    _require(
        public_pass.get("classification") == "research_log_not_authoritative_evidence",
        "Public search log classification drifted",
    )
    _require(
        public_pass.get("new_authoritative_numeric_task_lookup_recovered") is False,
        "Public search log cannot assert an authoritative recovered lookup",
    )

    state = _mapping(payload, "resolution_state")
    _require(
        state.get("authoritative_numeric_mapping_recovered") is False,
        "Authoritative GIW numeric mapping must remain unresolved",
    )
    _require(
        state.get("complete_mapping_recorded") is False,
        "Complete GIW numeric mapping must remain unrecorded",
    )
    _require(
        state.get("publication_order_used_as_numeric_mapping") is False,
        "Publication order must not be promoted to numeric mapping",
    )
    _require(
        state.get("task_directory_order_used_as_numeric_mapping") is False,
        "Task-directory order must not be promoted to numeric mapping",
    )
    _require(
        state.get("secondary_mapping_promoted_to_authoritative") is False,
        "ACE-DNV secondary corroboration cannot be promoted to authority",
    )
    _require(
        state.get("secondary_corroboration") == EXPECTED_SECONDARY,
        "ACE-DNV partial secondary corroboration drifted",
    )
    trial4 = _mapping(state, "trial_index_4")
    _require(
        trial4
        == {
            "status": "unresolved",
            "explicit_authoritative_binding_found": False,
            "explicit_secondary_binding_found": False,
            "tea_making_inferred_by_elimination": False,
        },
        "TrIdx 4 must remain unresolved and not inferred as Tea_Making",
    )
    _require(
        state.get("task_stratified_validation_authorized") is False,
        "Task-stratified GIW validation remains unauthorized",
    )

    boundary = _mapping(payload, "scientific_boundary")
    _require(
        set(boundary) == EXPECTED_BOUNDARY_KEYS,
        "GIW task-mapping exhaustion scientific-boundary contract drifted",
    )
    _require(
        not any(bool(value) for value in boundary.values()),
        "GIW task-mapping exhaustion cannot promote scientific gates",
    )

    scope_statement = _mapping(payload, "scope_statement")
    _require(
        scope_statement
        == {
            "enumerated_reviewed_scope_exhausted": True,
            "global_nonexistence_claimed": False,
        },
        "GIW task-mapping exhaustion scope statement drifted",
    )

    claim_limit = payload.get("claim_limit")
    _require(
        isinstance(claim_limit, str)
        and "does not prove that no mapping exists anywhere" in claim_limit
        and "Publication task order" in claim_limit
        and "ACE-DNV remains secondary corroboration" in claim_limit
        and "TrIdx 4 remains unresolved" in claim_limit
        and "Tea_Making is not inferred by elimination" in claim_limit,
        "GIW task-mapping exhaustion claim limit drifted",
    )

    return payload


def _validate_bound_upstream_files(evidence_path: Path) -> None:
    root = evidence_path.resolve().parents[3]
    for expected in EXPECTED_UPSTREAM_EVIDENCE:
        path = root / expected["path"]
        try:
            upstream = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise BenchmarkIntegrityError(
                f"Could not load bound GIW upstream evidence {path}: {exc}"
            ) from exc
        _require(
            isinstance(upstream, Mapping),
            f"Bound GIW upstream evidence {path} must be a JSON object",
        )
        field = expected["fingerprint_field"]
        _require(
            upstream.get(field) == expected["fingerprint_sha256"],
            f"Bound GIW upstream evidence fingerprint drifted for {path}",
        )


def load_gaze_in_wild_authoritative_task_mapping_exhaustion_evidence(
    path: str | Path,
) -> dict[str, Any]:
    """Load the frozen unresolved mapping record and recheck bound upstream files."""

    evidence_path = Path(path)
    try:
        record = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(
            f"Could not load GIW task-mapping exhaustion evidence: {exc}"
        ) from exc
    _require(
        isinstance(record, Mapping),
        "GIW task-mapping exhaustion evidence must be a JSON object",
    )
    validated = validate_gaze_in_wild_authoritative_task_mapping_exhaustion_evidence(
        record
    )
    _validate_bound_upstream_files(evidence_path)
    return validated
