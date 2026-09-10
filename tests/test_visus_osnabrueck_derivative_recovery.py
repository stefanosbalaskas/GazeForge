from __future__ import annotations

import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.visus_osnabrueck_derivative_recovery import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
    evidence_fingerprint,
    scenario_structural_fingerprint,
    validate_visus_osnabrueck_derivative_recovery,
)

EVIDENCE_PATH = (
    Path(__file__).parents[1]
    / "validation"
    / "evidence"
    / "visus-source-recheck"
    / "visus-osnabrueck-derivative-recovery-evidence-v1.json"
)


def _record() -> dict:
    return json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))


def _refingerprint(record: dict) -> dict:
    record["evidence_fingerprint_sha256"] = evidence_fingerprint(record)
    return record


def _refingerprint_scenario(record: dict, index: int) -> None:
    row = record["structural_recovery"]["scenario_structures"][index]
    row["scenario_structural_fingerprint_sha256"] = scenario_structural_fingerprint(row)


def test_committed_osnabrueck_derivative_recovery_validates() -> None:
    record = validate_visus_osnabrueck_derivative_recovery(EVIDENCE_PATH)
    assert record["evidence_fingerprint_sha256"] == EXPECTED_EVIDENCE_FINGERPRINT_SHA256


def test_osnabrueck_derivative_recovery_fingerprint_is_stable() -> None:
    assert evidence_fingerprint(_record()) == EXPECTED_EVIDENCE_FINGERPRINT_SHA256


def test_structural_recovery_is_kept_distinct_from_source_authority() -> None:
    boundary = _record()["authority_and_rights_boundary"]
    assert boundary["full_11_scenario_25_participant_derivative_structurally_recovered"] is True
    assert boundary["historical_institutional_derivative_distribution_recovered"] is True
    assert boundary["current_authoritative_original_visus_copy_recovered"] is False
    assert boundary["exact_original_visus_file_identity_proven"] is False


def test_all_eleven_scenarios_preserve_exact_participant_roster() -> None:
    recovery = _record()["structural_recovery"]
    assert recovery["scenario_count"] == 11
    assert len(recovery["scenario_structures"]) == 11
    for row in recovery["scenario_structures"]:
        assert row["participant_track_count"] == 25
        assert row["participant_numbers"] == list(range(1, 26))
        assert row["task_group_counts"] == {"A": 13, "B": 12}


def test_all_eleven_scenarios_preserve_published_video_geometry() -> None:
    for row in _record()["structural_recovery"]["scenario_structures"]:
        assert row["video"]["width"] == 1920
        assert row["video"]["height"] == 1080
        assert row["video"]["avg_frame_rate"] == "25/1"


@pytest.mark.parametrize(
    "key",
    [
        "current_authoritative_original_visus_copy_recovered",
        "exact_original_visus_file_identity_proven",
        "original_visus_dataset_license_resolved",
        "analysis_use_rights_resolved",
        "raw_source_redistribution_rights_resolved",
        "legacy_insecure_tls_retrieval_is_authority_evidence",
        "annotation_identity_to_original_viper_xml_proven",
        "independent_annotation_streams_verified",
        "source_audit_stage_authorized",
        "human_human_validation_authorized",
        "model_human_validation_authorized",
        "cross_dataset_validation_authorized",
        "native_60hz_gp3_validity_authorized",
        "empirical_frozen_evidence_authorized",
        "raw_source_redistribution_authorized",
        "new_empirical_performance_claim_authorized",
    ],
)
def test_refingerprinted_authority_or_empirical_promotions_are_rejected(key: str) -> None:
    record = _record()
    record["authority_and_rights_boundary"][key] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_osnabrueck_derivative_recovery(record)


def test_research_purpose_statement_cannot_become_formal_dataset_license() -> None:
    record = _record()
    record["institutional_derivative_source"][
        "research_purpose_statement_is_formal_dataset_license"
    ] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_osnabrueck_derivative_recovery(record)


def test_jemr_article_license_cannot_become_derivative_dataset_license() -> None:
    record = _record()
    record["conversion_method_evidence"][
        "jemr_article_license_is_visus_derivative_dataset_license"
    ] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_osnabrueck_derivative_recovery(record)


def test_usf_lossless_statement_cannot_become_independent_transform_fidelity_proof() -> None:
    record = _record()
    record["conversion_method_evidence"][
        "converter_transform_fidelity_independently_proven_for_this_archive"
    ] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_osnabrueck_derivative_recovery(record)


def test_legacy_insecure_tls_is_recorded_but_never_promoted_to_authority() -> None:
    record = _record()
    source = record["institutional_derivative_source"]
    assert source["legacy_host_tls_verification_succeeded"] is False
    assert source["legacy_host_insecure_tls_retrieval_used"] is True
    boundary = record["authority_and_rights_boundary"]
    assert boundary["legacy_insecure_tls_retrieval_is_authority_evidence"] is False


def test_missing_participant_is_rejected_even_after_scenario_and_record_refingerprinting() -> None:
    record = _record()
    row = record["structural_recovery"]["scenario_structures"][4]
    row["participant_numbers"].pop()
    row["participant_track_count"] = 24
    _refingerprint_scenario(record, 4)
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_osnabrueck_derivative_recovery(record)


def test_group_count_drift_is_rejected_even_after_refingerprinting() -> None:
    record = _record()
    row = record["structural_recovery"]["scenario_structures"][8]
    row["task_group_counts"] = {"A": 12, "B": 13}
    _refingerprint_scenario(record, 8)
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_osnabrueck_derivative_recovery(record)


def test_aoi_label_mutation_is_rejected_even_after_refingerprinting() -> None:
    record = _record()
    row = record["structural_recovery"]["scenario_structures"][9]
    row["aoi_titles"][4] = "Persons"
    _refingerprint_scenario(record, 9)
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_osnabrueck_derivative_recovery(record)


def test_video_frame_rate_mutation_is_rejected_even_after_refingerprinting() -> None:
    record = _record()
    row = record["structural_recovery"]["scenario_structures"][10]
    row["video"]["avg_frame_rate"] = "60/1"
    _refingerprint_scenario(record, 10)
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_osnabrueck_derivative_recovery(record)


def test_probe_report_hash_cannot_drift() -> None:
    record = _record()
    record["probe_bindings"][0]["raw_file_sha256"] = "0" * 64
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_osnabrueck_derivative_recovery(record)


def test_reconnaissance_artifact_digest_cannot_drift() -> None:
    record = _record()
    record["source_binding"]["artifact_digest_sha256"] = "0" * 64
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_osnabrueck_derivative_recovery(record)


def test_prior_source_recheck_binding_cannot_drift() -> None:
    record = _record()
    record["source_binding"][
        "authoritative_source_recheck_record_fingerprint_sha256"
    ] = "0" * 64
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_osnabrueck_derivative_recovery(record)


def test_prior_supplement_recovery_binding_cannot_drift() -> None:
    record = _record()
    record["source_binding"][
        "supplement_recovery_exhaustion_evidence_fingerprint_sha256"
    ] = "0" * 64
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_osnabrueck_derivative_recovery(record)
