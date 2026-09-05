from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.hollywood2_annotation_provenance import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
    evidence_fingerprint,
    load_hollywood2_annotation_provenance_evidence,
    validate_hollywood2_annotation_provenance_evidence,
)

EVIDENCE = Path(
    "validation/evidence/hollywood2/"
    "hollywood2-annotation-provenance-evidence-v1.json"
)


def _record() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def _refingerprint(record: dict) -> dict:
    record["evidence_fingerprint_sha256"] = evidence_fingerprint(record)
    return record


def test_committed_hollywood2_annotation_provenance_validates() -> None:
    record = validate_hollywood2_annotation_provenance_evidence(EVIDENCE)
    assert record["author_declaration"]["author_open_source_declaration_verified"] is True
    assert record["rights_interpretation"]["analysis_use_terms_status"] == "unresolved"
    assert record["upstream_participant_context"]["participant_identity_mapping_verified"] is False


def test_hollywood2_annotation_provenance_loader_preserves_boundary() -> None:
    loaded = load_hollywood2_annotation_provenance_evidence(EVIDENCE)
    assert loaded.fingerprint_sha256 == EXPECTED_EVIDENCE_FINGERPRINT_SHA256
    assert loaded.author_open_source_declaration_verified is True
    assert loaded.exact_license_identifier_verified is False
    assert loaded.participant_identity_mapping_verified is False


def test_author_declaration_cannot_be_promoted_to_exact_license_identifier() -> None:
    record = copy.deepcopy(_record())
    record["rights_interpretation"]["exact_license_identifier_verified"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="exact license identifier"):
        validate_hollywood2_annotation_provenance_evidence(record)


def test_author_declaration_cannot_be_promoted_to_redistribution_permission() -> None:
    record = copy.deepcopy(_record())
    record["rights_interpretation"]["raw_data_redistribution_terms_status"] = "verified"
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="redistribution status"):
        validate_hollywood2_annotation_provenance_evidence(record)


def test_upstream_unique_ids_cannot_promote_gin_token_mapping() -> None:
    record = copy.deepcopy(_record())
    record["upstream_participant_context"][
        "gin_tokens_authoritatively_linked_to_original_unique_subject_ids"
    ] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="GIN-to-original subject-ID linkage"):
        validate_hollywood2_annotation_provenance_evidence(record)


def test_upstream_unique_ids_cannot_promote_participant_identity_mapping() -> None:
    record = copy.deepcopy(_record())
    record["upstream_participant_context"]["participant_identity_mapping_verified"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="participant identity mapping"):
        validate_hollywood2_annotation_provenance_evidence(record)


def test_article_license_cannot_be_promoted_to_annotation_dataset_license() -> None:
    record = copy.deepcopy(_record())
    record["rights_interpretation"]["article_cc_by_is_dataset_license"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="article license as dataset license"):
        validate_hollywood2_annotation_provenance_evidence(record)


def test_hollywood2_annotation_provenance_fingerprint_is_frozen() -> None:
    record = _record()
    assert evidence_fingerprint(record) == EXPECTED_EVIDENCE_FINGERPRINT_SHA256
