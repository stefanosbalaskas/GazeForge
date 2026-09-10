from __future__ import annotations

import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.visus_supplement_recovery_exhaustion import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
    evidence_fingerprint,
    validate_visus_supplement_recovery_exhaustion,
)

EVIDENCE_PATH = (
    Path(__file__).parents[1]
    / "validation"
    / "evidence"
    / "visus-source-recheck"
    / "visus-2021-supplement-recovery-exhaustion-evidence-v1.json"
)


def _record() -> dict:
    return json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))


def _refingerprint(record: dict) -> dict:
    record["evidence_fingerprint_sha256"] = evidence_fingerprint(record)
    return record


def test_committed_supplement_recovery_checkpoint_validates() -> None:
    record = validate_visus_supplement_recovery_exhaustion(EVIDENCE_PATH)
    assert record["evidence_fingerprint_sha256"] == EXPECTED_EVIDENCE_FINGERPRINT_SHA256


def test_supplement_recovery_fingerprint_is_stable() -> None:
    assert evidence_fingerprint(_record()) == EXPECTED_EVIDENCE_FINGERPRINT_SHA256


def test_paper_statement_and_recovery_result_are_kept_distinct() -> None:
    record = _record()
    assert record["paper_statement"]["supplementary_material_explicitly_stated"] is True
    assert record["recovery_boundary"]["supplement_object_recovered"] is False
    assert record["recovery_boundary"]["supplement_never_existed_conclusion"] is False


@pytest.mark.parametrize(
    ("section", "key"),
    [
        ("recovery_boundary", "supplement_object_recovered"),
        ("recovery_boundary", "supplement_url_resolved"),
        ("recovery_boundary", "supplement_bytes_downloaded"),
        ("recovery_boundary", "supplement_contents_inspected"),
        ("recovery_boundary", "supplement_never_existed_conclusion"),
        ("recovery_boundary", "all_possible_public_surfaces_exhaustively_proven_negative"),
        ("recovery_boundary", "blind_url_guessing_authorized"),
        ("scientific_boundary", "full_visus_authoritative_source_recovered"),
        ("scientific_boundary", "visus_dataset_license_resolved"),
        ("scientific_boundary", "analysis_use_rights_resolved"),
        ("scientific_boundary", "raw_source_redistribution_rights_resolved"),
        ("scientific_boundary", "source_audit_stage_authorized"),
        ("scientific_boundary", "participant_stimulus_mapping_verified"),
        ("scientific_boundary", "annotation_independence_verified"),
        ("scientific_boundary", "human_human_validation_created"),
        ("scientific_boundary", "model_human_validation_created"),
        ("scientific_boundary", "cross_dataset_validation_created"),
        ("scientific_boundary", "native_60hz_gp3_validity_created"),
        ("scientific_boundary", "frozen_evidence_created"),
        ("scientific_boundary", "raw_source_redistributed"),
        ("scientific_boundary", "new_empirical_performance_claim_created"),
    ],
)
def test_refingerprinted_promotions_are_rejected(section: str, key: str) -> None:
    record = _record()
    record[section][key] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_supplement_recovery_exhaustion(record)


def test_mdpi_403_cannot_be_promoted_to_absence_evidence() -> None:
    record = _record()
    record["reviewed_surface_findings"]["current_mdpi_routes"][
        "access_denial_is_absence_evidence"
    ] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_supplement_recovery_exhaustion(record)


def test_candidate_filename_404s_cannot_become_authoritative() -> None:
    record = _record()
    static = record["reviewed_surface_findings"]["mdpi_static_attachment_candidates"]
    static["candidate_naming_authoritative"] = True
    static["candidate_404s_prove_original_filename"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_supplement_recovery_exhaustion(record)


def test_wayback_timeouts_preserve_non_exhaustive_boundary() -> None:
    record = _record()
    static = record["reviewed_surface_findings"]["wayback_static_attachment_namespace"]
    assert static["timeout_count"] == 2
    assert static["complete_negative_search_established"] is False
    static["complete_negative_search_established"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_supplement_recovery_exhaustion(record)


def test_archived_2022_xml_has_no_candidate_supplement_link() -> None:
    record = _record()
    archived = record["reviewed_surface_findings"]["wayback_archived_article"]
    assert archived["xml_2022_http_status"] == 200
    assert archived["xml_2022_supplement_text_marker_present"] is True
    assert archived["xml_2022_candidate_link_count"] == 0
    archived["historical_supplement_link_count"] = 1
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_supplement_recovery_exhaustion(record)


def test_probe_artifact_binding_cannot_drift() -> None:
    record = _record()
    record["source_binding"]["artifact_digest_sha256"] = "0" * 64
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_supplement_recovery_exhaustion(record)


def test_existing_authoritative_source_recheck_binding_cannot_drift() -> None:
    record = _record()
    record["source_binding"][
        "authoritative_source_recheck_record_fingerprint_sha256"
    ] = "0" * 64
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_supplement_recovery_exhaustion(record)


def test_remaining_routes_do_not_allow_blind_url_enumeration() -> None:
    record = _record()
    routes = record["remaining_authoritative_resolution_routes"]
    routes[0]["route"] = "blind-url-enumeration"
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_supplement_recovery_exhaustion(record)
