"""Validate frozen Gaze-in-the-Wild task-identity source-recovery evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

RECORD_TYPE = "gaze-in-wild-task-identity-source-recovery-evidence-v1"
PINNED_REPOSITORY = "https://github.com/RSKothari/Gaze-in-Wild"
PINNED_COMMIT = "52262d44e366a53369e10ca73c5f41daf0e8f1e5"
MLAPP_BLOB = "2d560af336af637e042ea7a96f4c3736a59d2a2f"
MLAPP_SHA256 = "38eaa6acbd47ec6a35f750d715c2a2dc9e0b22e1c9bc9414c353dc4f8d209693"
PLOT_LABELS_BLOB = "511581250e04c62037c71d2da16271be4979d434"
EXPECTED_PARENTS = {
    "figshare_public_metadata_summary_fingerprint_sha256":
        "32b14b0daf4d73204fc52b1da2205d634097a934c51746798b4c2205e620389d",
    "historical_tree_recovery_fingerprint_sha256":
        "f144f5b7edcdbd02e85b53e751812c41b6567105219fbfb63c097bcefc5c9ffc",
    "participant_task_metadata_fingerprint_sha256":
        "55b279fadd969e23b535fff3aac92327a45eb89cd0f365d90c0e5c6cae351017",
}
FALSE_BOUNDARIES = (
    "universal_tridx_to_task_mapping_verified",
    "complete_per_file_task_mapping_verified",
    "participant_disjoint_model_validation_created",
    "human_human_agreement_created",
    "cross_dataset_validation_created",
    "gp3_validity_claim_created",
    "quarantine_exit_authorized",
    "new_empirical_performance_claim_created",
)


class TaskIdentitySourceRecoveryEvidenceError(ValueError):
    """Raised when reviewed task-identity source-recovery evidence drifts."""


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def evidence_fingerprint(record: dict[str, Any]) -> str:
    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def load_evidence(path: str | Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TaskIdentitySourceRecoveryEvidenceError(
            f"Could not load task-identity source-recovery evidence: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise TaskIdentitySourceRecoveryEvidenceError("Evidence root must be an object.")
    return validate_evidence(value)


def validate_evidence(record: dict[str, Any]) -> dict[str, Any]:
    if record.get("record_type") != RECORD_TYPE:
        raise TaskIdentitySourceRecoveryEvidenceError("Unexpected evidence record type.")
    if record.get("status") != (
        "pinned-first-party-task-identity-route-exhausted-no-explicit-mapping-recovered"
    ):
        raise TaskIdentitySourceRecoveryEvidenceError("Reviewed status drifted.")

    scope = _mapping(record, "source_scope")
    expected_scope = {
        "repository": PINNED_REPOSITORY,
        "pinned_commit_sha1": PINNED_COMMIT,
        "reachable_commit_count": 56,
        "unique_text_blob_count": 302,
        "task_related_blob_count": 1,
    }
    if scope != expected_scope:
        raise TaskIdentitySourceRecoveryEvidenceError("Pinned source scope drifted.")

    parents = _mapping(record, "parent_evidence")
    if parents != EXPECTED_PARENTS:
        raise TaskIdentitySourceRecoveryEvidenceError("Parent evidence binding drifted.")

    mlapp = _mapping(record, "mlapp_audit")
    if mlapp.get("path") != "GIWApp.mlapp":
        raise TaskIdentitySourceRecoveryEvidenceError("MLAPP path drifted.")
    if mlapp.get("git_blob_sha1") != MLAPP_BLOB:
        raise TaskIdentitySourceRecoveryEvidenceError("MLAPP Git blob drifted.")
    if mlapp.get("sha256") != MLAPP_SHA256:
        raise TaskIdentitySourceRecoveryEvidenceError("MLAPP SHA-256 drifted.")
    if mlapp.get("size_bytes") != 99_566 or mlapp.get("member_count") != 9:
        raise TaskIdentitySourceRecoveryEvidenceError("MLAPP container identity drifted.")
    if mlapp.get("zip_container") is not True:
        raise TaskIdentitySourceRecoveryEvidenceError("MLAPP must remain a ZIP container.")
    if mlapp.get("task_context_count") != 0:
        raise TaskIdentitySourceRecoveryEvidenceError(
            "Reviewed MLAPP task-context result drifted."
        )
    members = mlapp.get("members")
    if not isinstance(members, list) or len(members) != 9:
        raise TaskIdentitySourceRecoveryEvidenceError("MLAPP member inventory drifted.")
    expected_member_names = {
        "[Content_Types].xml",
        "_rels/.rels",
        "appdesigner/appModel.mat",
        "matlab/document.xml",
        "metadata/appMetadata.xml",
        "metadata/appScreenshot.png",
        "metadata/coreProperties.xml",
        "metadata/mwcoreProperties.xml",
        "metadata/mwcorePropertiesExtension.xml",
    }
    if {row.get("name") for row in members if isinstance(row, dict)} != expected_member_names:
        raise TaskIdentitySourceRecoveryEvidenceError("MLAPP member names drifted.")

    history = _mapping(record, "reachable_history_observation")
    expected_history = {
        "explicit_task_to_trial_mapping_recovered": False,
        "identity_plus_tridx_candidate_context_count": 0,
        "nearby_tridx_assignments": [],
        "only_task_related_git_blob_sha1": PLOT_LABELS_BLOB,
        "only_task_related_path": "PlotLabels.m",
        "task_context_count": 2,
        "task_terms": ["giw_rearranged", "indoor_walk"],
    }
    if history != expected_history:
        raise TaskIdentitySourceRecoveryEvidenceError(
            "Reviewed reachable-history observation drifted."
        )

    binding = _mapping(record, "probe_binding")
    expected_binding = {
        "workflow_run_id": 34163709562,
        "artifact_id": 10033447214,
        "artifact_name": "gaze-in-wild-task-identity-recovery-probe",
        "artifact_zip_sha256":
            "117aec161bcc1d75eafc612f160c54a4d33381fcae6e5fe24c2216a6867ddcae",
        "probe_fingerprint_sha256":
            "3821dd2f2e0cd720c34837a1f20b51bb208c584739054b4a4543ce0048acbd57",
        "exact_gazeforge_head_sha1":
            "a7b21c151439e03ad29e4e157024f83062186bab",
    }
    if binding != expected_binding:
        raise TaskIdentitySourceRecoveryEvidenceError("Probe binding drifted.")

    limits = record.get("claim_limits")
    if not isinstance(limits, list) or len(limits) < 4:
        raise TaskIdentitySourceRecoveryEvidenceError("Claim limits are incomplete.")
    joined = " ".join(str(x) for x in limits)
    required_phrases = (
        "not proof that no mapping exists",
        "not promoted into a universal TrIdx-to-task lookup",
        "do not justify a universal task-number mapping",
        "No participant-disjoint model validation",
    )
    for phrase in required_phrases:
        if phrase not in joined:
            raise TaskIdentitySourceRecoveryEvidenceError(
                f"Required claim limit is missing: {phrase}"
            )

    boundary = _mapping(record, "scientific_boundary")
    if set(boundary) != set(FALSE_BOUNDARIES):
        raise TaskIdentitySourceRecoveryEvidenceError("Scientific boundary keys drifted.")
    for key in FALSE_BOUNDARIES:
        if boundary.get(key) is not False:
            raise TaskIdentitySourceRecoveryEvidenceError(f"{key} must remain false.")

    observed = record.get("evidence_fingerprint_sha256")
    expected = evidence_fingerprint(record)
    if observed != expected:
        raise TaskIdentitySourceRecoveryEvidenceError("Evidence fingerprint mismatch.")
    return record


def _mapping(record: dict[str, Any], key: str) -> dict[str, Any]:
    value = record.get(key)
    if not isinstance(value, dict):
        raise TaskIdentitySourceRecoveryEvidenceError(f"{key} must be an object.")
    return value
