from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.hollywood2_rights_evidence import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
    evidence_fingerprint,
    load_hollywood2_rights_evidence,
    validate_hollywood2_rights_evidence,
)

EVIDENCE = Path(
    "validation/evidence/hollywood2/"
    "hollywood2-underlying-source-rights-evidence-v1.json"
)


def _record() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def _refingerprint(record: dict) -> dict:
    record["evidence_fingerprint_sha256"] = evidence_fingerprint(record)
    return record


def test_committed_hollywood2_rights_evidence_validates() -> None:
    record = validate_hollywood2_rights_evidence(EVIDENCE)
    assert record["recording_context"]["participant_count"] == 16
    assert record["underlying_rights"]["analysis_use_terms_status"] == (
        "verified_academic_use_only"
    )
    assert record["underlying_rights"]["raw_archive_redistribution_status"] == (
        "not_permitted_under_standard_grant"
    )


def test_hollywood2_rights_loader_preserves_scope() -> None:
    loaded = load_hollywood2_rights_evidence(EVIDENCE)
    assert loaded.fingerprint_sha256 == EXPECTED_EVIDENCE_FINGERPRINT_SHA256
    assert loaded.participant_count == 16
    assert loaded.analysis_use_terms_status == "verified_academic_use_only"
    assert loaded.raw_archive_redistribution_status == (
        "not_permitted_under_standard_grant"
    )


def test_hollywood2_rights_cannot_promote_standard_transfer() -> None:
    record = copy.deepcopy(_record())
    record["underlying_rights"]["standard_grant_allows_dataset_transfer"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="dataset transfer"):
        validate_hollywood2_rights_evidence(record)


def test_hollywood2_underlying_licence_cannot_be_inherited_by_gin() -> None:
    record = copy.deepcopy(_record())
    record["annotation_repository_rights"][
        "underlying_license_automatically_applies_to_annotation_repository"
    ] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="automatic licence inheritance"):
        validate_hollywood2_rights_evidence(record)


def test_hollywood2_token_count_does_not_authorize_participant_mapping() -> None:
    record = copy.deepcopy(_record())
    record["participant_mapping"]["file_subject_token_to_participant_mapping_verified"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="token mapping"):
        validate_hollywood2_rights_evidence(record)


def test_hollywood2_access_gate_cannot_be_promoted_to_archive_recovery() -> None:
    record = copy.deepcopy(_record())
    record["institutional_source"]["download_endpoint"][
        "anonymous_direct_archive_access_verified"
    ] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="anonymous archive access"):
        validate_hollywood2_rights_evidence(record)


def test_hollywood2_rights_evidence_fingerprint_is_frozen() -> None:
    record = _record()
    assert evidence_fingerprint(record) == EXPECTED_EVIDENCE_FINGERPRINT_SHA256
