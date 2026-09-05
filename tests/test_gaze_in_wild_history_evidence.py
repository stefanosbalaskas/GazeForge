import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_history_evidence import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
    EXPECTED_PROBE_FINGERPRINT_SHA256,
    load_gaze_in_wild_repository_history_evidence,
    validate_gaze_in_wild_repository_history_evidence,
)

_EVIDENCE = Path(
    "validation/evidence/gaze-in-wild/gaze-in-wild-repository-history-evidence-v1.json"
)


def _record():
    return json.loads(_EVIDENCE.read_text(encoding="utf-8"))


def test_gaze_in_wild_repository_history_evidence_validates():
    record = validate_gaze_in_wild_repository_history_evidence(_EVIDENCE)

    assert record["evidence_fingerprint_sha256"] == EXPECTED_EVIDENCE_FINGERPRINT_SHA256
    assert record["execution"]["live_probe_fingerprint_sha256"] == (
        EXPECTED_PROBE_FINGERPRINT_SHA256
    )
    assert record["repository_history"]["reachable_commit_count"] == 56
    assert record["repository_history"]["root_commit_sha1"] == (
        "054c99d3b88f0ad46cbd0b7d66f4fc38718046f5"
    )
    assert record["readme_history"]["unique_blob_count"] == 6


def test_gaze_in_wild_repository_history_typed_loader_preserves_boundaries():
    evidence = load_gaze_in_wild_repository_history_evidence(_EVIDENCE)

    assert evidence.commit_count == 56
    assert evidence.repository_mit_verified_for_software is True
    assert evidence.exact_dataset_copy_obtained is False
    assert evidence.participant_identity_mapping_verified is False


def test_gaze_in_wild_repository_history_scopes_mit_to_software():
    record = _record()
    license_history = record["software_license_history"]
    boundary = record["scientific_boundary"]

    assert license_history["license_file_identifies_mit"] is True
    assert license_history["license_scope"] == "software and associated documentation files"
    assert license_history["license_scope_promoted_to_external_dataset_files"] is False
    assert boundary["repository_mit_license_verified_for_software"] is True
    assert boundary["external_dataset_file_license_verified"] is False
    assert boundary["software_mit_is_external_dataset_license"] is False


def test_gaze_in_wild_repository_history_does_not_promote_historical_download_url():
    record = _record()

    assert record["readme_history"]["pinned_distribution_url_present"] is True
    assert record["readme_history"][
        "pinned_all_data_files_download_webpage_statement_present"
    ] is True
    assert record["scientific_boundary"]["exact_external_dataset_copy_obtained"] is False
    assert record["scientific_boundary"][
        "published_distribution_url_is_current_direct_copy_verified"
    ] is False


def test_gaze_in_wild_repository_history_does_not_promote_mapping_or_performance():
    boundary = _record()["scientific_boundary"]

    assert boundary["participant_identity_mapping_from_history_verified"] is False
    assert boundary["complete_trial_to_task_mapping_from_history_verified"] is False
    assert boundary["human_human_agreement_created"] is False
    assert boundary["participant_disjoint_model_validation_created"] is False
    assert boundary["cross_dataset_validation_created"] is False
    assert boundary["gp3_validity_claim_created"] is False
    assert boundary["frozen_evidence_performance_claim_created"] is False


def test_gaze_in_wild_repository_history_rejects_dataset_license_promotion(tmp_path):
    record = _record()
    record["scientific_boundary"]["software_mit_is_external_dataset_license"] = True
    path = tmp_path / "history.json"
    path.write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="dataset license"):
        validate_gaze_in_wild_repository_history_evidence(path)


def test_gaze_in_wild_repository_history_rejects_participant_mapping_promotion(tmp_path):
    record = _record()
    record["scientific_boundary"]["participant_identity_mapping_from_history_verified"] = True
    path = tmp_path / "history.json"
    path.write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="participant mapping"):
        validate_gaze_in_wild_repository_history_evidence(path)


def test_gaze_in_wild_repository_history_rejects_fingerprint_drift(tmp_path):
    record = _record()
    record["repository_history"]["reachable_commit_count"] = 55
    path = tmp_path / "history.json"
    path.write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="commit count"):
        validate_gaze_in_wild_repository_history_evidence(path)
