from __future__ import annotations

import hashlib
import json
from pathlib import Path

PROTOCOL = Path(
    "validation/protocols/hollywood2-participant-ledger-intake-v1.json"
)
EXPECTED_FINGERPRINT = (
    "b47cc0acea2ded577d140d38ca97ad71ce414d82a41b2675e5cac6fc2dc9135b"
)


def _fingerprint(record: dict) -> str:
    body = dict(record)
    body.pop("protocol_fingerprint_sha256", None)
    canonical = json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def test_participant_ledger_intake_protocol_is_frozen() -> None:
    record = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert record["record_type"] == "hollywood2-participant-ledger-intake-protocol-v1"
    assert record["status"] == "ready-for-authorized-local-archive-metadata-inspection"
    assert record["created_on"] == "2026-09-10"
    assert record["protocol_fingerprint_sha256"] == EXPECTED_FINGERPRINT
    assert _fingerprint(record) == EXPECTED_FINGERPRINT

    context = record["source_context"]
    assert context["public_original_subject_count"] == 16
    assert context["public_active_subject_count"] == 12
    assert context["public_free_viewing_subject_count"] == 4
    assert context["dissertation_reports_unique_subject_ids_within_task_groups"] is True
    assert context["authoritative_archive_readme_or_subject_ledger_bytes_recovered"] is False
    assert context["gin_source_token_count"] == 16
    assert context["gin_token_count_match_is_mapping_evidence"] is False

    intake = record["intake_contract"]
    assert intake["caller_must_affirm_authorized_local_copy"] is True
    assert intake["automatic_network_download_performed"] is False
    assert intake["archive_extraction_performed"] is False
    assert intake["raw_gaze_members_opened"] is False
    assert intake["metadata_candidates_only"] is True
    assert intake["metadata_text_committed"] is False
    assert intake["metadata_hashes_and_markers_only"] is True

    gate = record["promotion_gate"]
    assert gate["metadata_marker_detection_is_mapping_evidence"] is False
    assert gate["subject_id_like_pattern_count_is_mapping_evidence"] is False
    assert gate["filename_token_count_match_is_mapping_evidence"] is False
    assert gate["participant_identity_mapping_verified"] is False
    assert gate["gin_token_to_original_subject_id_verified"] is False
    assert gate["gin_token_to_task_group_verified"] is False
    assert gate["participant_disjoint_model_validation_created"] is False
    assert gate["manual_authoritative_ledger_review_required"] is True

    rights = record["rights_boundary"]
    assert all(value is False for value in rights.values())
    scientific = record["scientific_boundary"]
    assert all(value is False for value in scientific.values())
