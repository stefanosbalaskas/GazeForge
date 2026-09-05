from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.hollywood2_history_evidence import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
    evidence_fingerprint,
    load_hollywood2_gin_history_evidence,
    validate_hollywood2_gin_history_evidence,
    validate_hollywood2_gin_history_probe,
)

EVIDENCE = Path(
    "validation/evidence/hollywood2/hollywood2-gin-history-evidence-v1.json"
)


def _record() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def _refingerprint(record: dict) -> dict:
    record["evidence_fingerprint_sha256"] = evidence_fingerprint(record)
    return record


def _matching_probe() -> dict:
    record = _record()
    ground = record["ground_truth_path_history"]
    repository = record["repository_history"]
    license_history = record["license_history"]
    readme = record["readme_history"]
    return {
        "record_type": "hollywood2-gin-history-probe-v1",
        "repository": record["scope"]["repository"],
        "pinned_head_sha1": record["scope"]["pinned_commit_sha1"],
        "observed_head_sha1": record["scope"]["pinned_commit_sha1"],
        "history": {
            "commit_count": repository["commit_count"],
            "initial_commit_sha1": repository["initial_commit_sha1"],
            "head_commit_sha1": repository["head_commit_sha1"],
            "license_history": {
                "license_named_file_ever_present": license_history[
                    "license_or_copying_named_file_ever_present"
                ],
                "occurrence_count": license_history["license_named_file_occurrence_count"],
            },
            "readme_history": {
                "unique_version_count": readme["unique_version_count"],
                "license_keyword_ever_present": license_history[
                    "readme_license_or_licence_keyword_ever_present"
                ],
                "identity_keyword_ever_present": readme[
                    "participant_or_identity_keyword_ever_present"
                ],
            },
            "ground_truth_history": {
                "current": {
                    "file_count": ground["ground_truth_file_count"],
                    "clip_count": ground["clip_count"],
                    "file_subject_token_count": ground["file_subject_token_count"],
                    "file_subject_tokens": ground["file_subject_tokens"],
                    "path_fingerprint_sha256": ground[
                        "ground_truth_path_fingerprint_sha256"
                    ],
                },
                "token_set_version_count": ground["token_set_version_count"],
                "path_inventory_version_count": ground["path_inventory_version_count"],
                "first_seen_fingerprint_sha256": ground[
                    "first_seen_fingerprint_sha256"
                ],
            },
        },
    }


def test_committed_hollywood2_history_evidence_validates() -> None:
    record = validate_hollywood2_gin_history_evidence(EVIDENCE)
    assert record["repository_history"]["commit_count"] == 7
    assert record["license_history"]["license_or_copying_named_file_ever_present"] is False
    assert record["readme_history"]["participant_or_identity_keyword_ever_present"] is False
    assert record["ground_truth_path_history"]["token_set_version_count"] == 1


def test_hollywood2_history_loader_preserves_boundary() -> None:
    loaded = load_hollywood2_gin_history_evidence(EVIDENCE)
    assert loaded.fingerprint_sha256 == EXPECTED_EVIDENCE_FINGERPRINT_SHA256
    assert loaded.commit_count == 7
    assert loaded.repository_license_file_recovered is False
    assert loaded.participant_identity_mapping_verified is False


def test_historical_absence_cannot_be_promoted_to_license_recovery() -> None:
    record = copy.deepcopy(_record())
    record["scientific_boundary"]["historical_repository_license_file_recovered"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="historical license-file recovery"):
        validate_hollywood2_gin_history_evidence(record)


def test_stable_filename_tokens_cannot_be_promoted_to_participant_mapping() -> None:
    record = copy.deepcopy(_record())
    record["scientific_boundary"][
        "filename_token_to_original_participant_id_mapping_verified"
    ] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="filename-token participant mapping"):
        validate_hollywood2_gin_history_evidence(record)


def test_stable_filename_tokens_cannot_unlock_participant_disjoint_modelling() -> None:
    record = copy.deepcopy(_record())
    record["scientific_boundary"]["participant_disjoint_model_validation_created"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="participant-disjoint modelling"):
        validate_hollywood2_gin_history_evidence(record)


def test_live_history_probe_binds_to_frozen_evidence() -> None:
    probe = _matching_probe()
    validated = validate_hollywood2_gin_history_probe(probe, EVIDENCE)
    assert validated["history"]["commit_count"] == 7


def test_live_history_probe_rejects_license_drift() -> None:
    probe = _matching_probe()
    probe["history"]["license_history"]["license_named_file_ever_present"] = True
    with pytest.raises(BenchmarkIntegrityError, match="live license history"):
        validate_hollywood2_gin_history_probe(probe, EVIDENCE)


def test_hollywood2_history_evidence_fingerprint_is_frozen() -> None:
    record = _record()
    assert evidence_fingerprint(record) == EXPECTED_EVIDENCE_FINGERPRINT_SHA256
