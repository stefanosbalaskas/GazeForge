from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from urllib.parse import quote

import pytest

from gazeforge import BenchmarkIntegrityError
from gazeforge.visus_public_event_extension import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
    EXPECTED_PROBE_FINGERPRINT_SHA256,
    evidence_fingerprint,
    load_visus_public_event_extension_evidence,
    validate_visus_public_event_extension_evidence,
    validate_visus_public_event_extension_probe,
)

EVIDENCE = (
    Path(__file__).parents[1]
    / "validation"
    / "evidence"
    / "visus-public-event-extension"
    / "visus-public-event-extension-evidence-v1.json"
)


def _record() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def _refingerprint(record: dict) -> dict:
    record["evidence_fingerprint_sha256"] = evidence_fingerprint(record)
    return record


def _probe_from_evidence() -> dict:
    record = _record()
    files = {}
    for key, spec in record["upstream"]["files"].items():
        path = spec["path"]
        files[key] = {
            **spec,
            "url": (
                "https://raw.githubusercontent.com/Maurice189/eye-slitscan/"
                "a8ea2402936122f9e5c98152460bd16a4ba97740/"
                + quote(path, safe="/")
            ),
        }
    probe = {
        "record_type": "visus-public-event-extension-probe-v1",
        "status": "probe_only",
        "upstream": {
            "repository": record["upstream"]["repository"],
            "commit": record["upstream"]["commit"],
            "files": files,
            "unit_test_provenance": copy.deepcopy(
                record["upstream"]["unit_test_provenance"]
            ),
        },
        "coverage": copy.deepcopy(record["coverage"]),
        "participants": copy.deepcopy(record["participants"]),
        "aggregate": copy.deepcopy(record["aggregate"]),
        "stimulus_inference": copy.deepcopy(record["stimulus_inference"]),
        "provenance_lockfiles": copy.deepcopy(record["provenance_lockfiles"]),
        "reuse_boundary": {
            "analysis_use_basis_recorded": True,
            "analysis_use_basis": record["reuse_boundary"]["analysis_use_basis"],
            "source_license_resolved": False,
            "source_bytes_redistributed_by_gazeforge": False,
            "unrestricted_redistribution_asserted": False,
        },
        "scientific_boundary": {
            "real_external_tobii_60hz_exports": True,
            "participant_identity_file_bound": True,
            "stimulus_identity_file_bound": False,
            "dialog_assignment_is_inference": True,
            "dynamic_aoi_metrics_created": False,
            "human_human_agreement_created": False,
            "model_validation_created": False,
            "native_gp3_evidence": False,
            "original_full_visus_source_resolved": False,
            "frozen_evidence_created": False,
        },
    }
    canonical = json.dumps(probe, sort_keys=True, separators=(",", ":")).encode()
    probe["probe_fingerprint_sha256"] = hashlib.sha256(canonical).hexdigest()
    return probe


def test_committed_visus_public_event_extension_evidence_validates() -> None:
    record = validate_visus_public_event_extension_evidence(EVIDENCE)
    assert record["status"] == "verified-partial-empirical"
    assert record["coverage"]["participants"] == ["P5B", "P3A"]
    assert record["aggregate"]["sample_count"] == 2290
    assert record["aggregate"]["valid_both_eye_samples"] == 2272
    assert record["aggregate"]["fixation_event_count"] == 105
    assert record["aggregate"]["fixations_with_on_screen_mapped_point"] == 104
    assert record["stimulus_inference"]["stimulus_identity_resolved"] is False
    assert record["evidence_fingerprint_sha256"] == EXPECTED_EVIDENCE_FINGERPRINT_SHA256


def test_compact_loader_reports_event_extension_identity() -> None:
    evidence = load_visus_public_event_extension_evidence(EVIDENCE)
    assert evidence.participant_count == 2
    assert evidence.sample_count == 2290
    assert evidence.fixation_event_count == 105
    assert evidence.observed_sampling_rate_hz == pytest.approx(60.150375939849624)
    assert evidence.stimulus_candidate == "03-dialog"
    assert evidence.stimulus_identity_resolved is False


def test_self_fingerprint_tampering_fails() -> None:
    record = _record()
    record["aggregate"]["sample_count"] += 1
    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_public_event_extension_evidence(record)


@pytest.mark.parametrize(
    "key",
    [
        "P5B",
        "P3A",
        "lock_P2B_dialog",
        "lock_P4B_dialog",
        "lock_P6A_dialog",
        "upstream_test_source",
    ],
)
def test_source_identity_drift_fails_even_when_refingerprinted(key: str) -> None:
    record = _record()
    record["upstream"]["files"][key]["sha256"] = "0" * 64
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="source-file ledger"):
        validate_visus_public_event_extension_evidence(record)


@pytest.mark.parametrize(
    ("section", "key", "value"),
    [
        ("coverage", "full_visus_recovered", True),
        ("stimulus_inference", "stimulus_identity_resolved", True),
        ("stimulus_inference", "aoi_annotation_recovered_for_candidate", True),
        ("reuse_boundary", "source_license_resolved", True),
        ("reuse_boundary", "unrestricted_redistribution_asserted", True),
        ("reuse_boundary", "source_bytes_redistributed_by_gazeforge", True),
        ("scientific_boundary", "stimulus_identity_file_bound", True),
        ("scientific_boundary", "dynamic_aoi_metrics_created", True),
        ("scientific_boundary", "human_human_agreement_created", True),
        ("scientific_boundary", "model_validation_created", True),
        ("scientific_boundary", "native_gp3_evidence", True),
        ("scientific_boundary", "original_full_visus_source_resolved", True),
        ("scientific_boundary", "frozen_evidence_created", True),
    ],
)
def test_claim_promotion_fails_even_when_refingerprinted(
    section: str, key: str, value: object
) -> None:
    record = _record()
    record[section][key] = value
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_public_event_extension_evidence(record)


def test_dialog_candidate_cannot_be_promoted_or_relabelled() -> None:
    record = _record()
    record["stimulus_inference"]["candidate"] = "01-car pursuit"
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="stimulus candidate"):
        validate_visus_public_event_extension_evidence(record)


def test_participant_coverage_drift_fails() -> None:
    record = _record()
    record["coverage"]["participants"] = ["P5B"]
    record["coverage"]["participant_count"] = 1
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="participants"):
        validate_visus_public_event_extension_evidence(record)


def test_upstream_unit_test_provenance_drift_fails() -> None:
    record = _record()
    record["upstream"]["unit_test_provenance"]["row_value_assertions_verified"] = False
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="unit-test provenance"):
        validate_visus_public_event_extension_evidence(record)


def test_aggregate_cannot_drift_from_participants() -> None:
    record = _record()
    record["participants"][0]["fixation_event_count"] += 1
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_public_event_extension_evidence(record)


def test_exported_fixation_durations_are_not_claimed_as_movie_clipped() -> None:
    record = _record()
    assert record["duration_semantics"]["exported_fixation_duration_sum_ms"] == 39614
    assert record["duration_semantics"]["participant_movie_span_sum_ms"] == 38132
    assert record["duration_semantics"]["fixation_durations_clipped_to_movie_boundaries"] is False

    record["duration_semantics"]["fixation_durations_clipped_to_movie_boundaries"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_public_event_extension_evidence(record)


def test_v1_fingerprint_is_immutable_even_for_self_consistent_rewrite() -> None:
    record = copy.deepcopy(_record())
    record["extra_claim"] = "not part of frozen v1"
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="immutable v1 fingerprint"):
        validate_visus_public_event_extension_evidence(record)


def test_live_probe_contract_binds_to_committed_evidence() -> None:
    probe = _probe_from_evidence()
    assert probe["probe_fingerprint_sha256"] == EXPECTED_PROBE_FINGERPRINT_SHA256
    result = validate_visus_public_event_extension_probe(probe, EVIDENCE)
    assert result["evidence_fingerprint_sha256"] == EXPECTED_EVIDENCE_FINGERPRINT_SHA256


def test_live_probe_drift_fails() -> None:
    probe = _probe_from_evidence()
    probe["participants"][0]["fixation_event_count"] += 1
    body = dict(probe)
    body.pop("probe_fingerprint_sha256")
    probe["probe_fingerprint_sha256"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_public_event_extension_probe(probe, EVIDENCE)
