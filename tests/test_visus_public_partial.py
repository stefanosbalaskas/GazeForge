from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from gazeforge import BenchmarkIntegrityError
from gazeforge.visus_public_partial import (
    evidence_fingerprint,
    load_visus_public_partial_evidence,
    validate_visus_public_partial_evidence,
    validate_visus_public_partial_probe,
)

EVIDENCE = (
    Path(__file__).parents[1]
    / "validation"
    / "evidence"
    / "visus-public-partial"
    / "visus-public-partial-evidence-v1.json"
)


def _record() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def _refingerprint(record: dict) -> dict:
    record["evidence_fingerprint_sha256"] = evidence_fingerprint(record)
    return record


def test_committed_visus_public_partial_evidence_validates() -> None:
    record = validate_visus_public_partial_evidence(EVIDENCE)
    assert record["status"] == "verified-partial-empirical"
    assert record["coverage"]["participants"] == ["P1A", "P2B", "P9B"]
    assert record["coverage"]["stimuli"] == ["01-car pursuit"]
    assert record["aggregate"]["sample_count"] == 4498
    assert record["aggregate"]["fixation_event_count"] == 185
    assert record["aggregate"]["fixation_events_hitting_any_dynamic_aoi"] == 166
    assert record["aggregate"]["fixation_duration_hitting_any_dynamic_aoi_ms"] == 70179
    assert record["aggregate"]["inferred_sampling_rate_hz"] == pytest.approx(
        60.150375939849624
    )


def test_compact_loader_reports_partial_identity() -> None:
    evidence = load_visus_public_partial_evidence(EVIDENCE)
    assert evidence.participant_count == 3
    assert evidence.stimulus_count == 1
    assert evidence.sample_count == 4498
    assert evidence.fixation_event_count == 185
    assert evidence.observed_sampling_rate_hz == pytest.approx(60.150375939849624)


def test_self_fingerprint_tampering_fails() -> None:
    record = _record()
    record["aggregate"]["sample_count"] += 1
    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_public_partial_evidence(record)


@pytest.mark.parametrize("key", ["aoi", "P1A", "P2B", "P9B"])
def test_source_identity_drift_fails_even_when_refingerprinted(key: str) -> None:
    record = _record()
    record["upstream"]["files"][key]["sha256"] = "0" * 64
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="source-file ledger"):
        validate_visus_public_partial_evidence(record)


@pytest.mark.parametrize(
    ("section", "key", "value"),
    [
        ("coverage", "full_visus_recovered", True),
        ("reuse_boundary", "unrestricted_redistribution_asserted", True),
        ("reuse_boundary", "source_license_resolved", True),
        ("scientific_boundary", "original_full_visus_source_resolved", True),
        ("scientific_boundary", "human_human_agreement_created", True),
        ("scientific_boundary", "native_gp3_evidence", True),
        ("scientific_boundary", "frozen_evidence_created", True),
        ("scientific_boundary", "model_validation_created", True),
    ],
)
def test_claim_promotion_fails_even_when_refingerprinted(
    section: str, key: str, value: object
) -> None:
    record = _record()
    record[section][key] = value
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_public_partial_evidence(record)


def test_participant_coverage_drift_fails() -> None:
    record = _record()
    record["coverage"]["participants"] = ["P1A", "P2B"]
    record["coverage"]["participant_count"] = 2
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="participants"):
        validate_visus_public_partial_evidence(record)


def test_stimulus_drift_fails() -> None:
    record = _record()
    record["coverage"]["stimuli"] = ["02-running away"]
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="stimuli"):
        validate_visus_public_partial_evidence(record)


def test_aggregate_cannot_drift_from_participants() -> None:
    record = _record()
    record["participants"][0]["fixation_event_count"] += 1
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="aggregate"):
        validate_visus_public_partial_evidence(record)


def test_v1_fingerprint_is_immutable_even_for_self_consistent_rewrite() -> None:
    record = copy.deepcopy(_record())
    record["claim_limits"] = list(record["claim_limits"]) + ["Unreviewed extra claim."]
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="not the frozen v1 record"):
        validate_visus_public_partial_evidence(record)


def _probe_from_evidence() -> dict:
    record = _record()
    files = {}
    from urllib.parse import quote

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
        "record_type": "visus-public-partial-probe-v1",
        "status": "probe_only",
        "upstream": {
            "repository": record["upstream"]["repository"],
            "commit": record["upstream"]["commit"],
            "files": files,
        },
        "coverage": copy.deepcopy(record["coverage"]),
        "aoi": copy.deepcopy(record["aoi"]),
        "participants": copy.deepcopy(record["participants"]),
        "scientific_boundary": {
            "frozen_evidence_created": False,
            "human_human_agreement_created": False,
            "native_gp3_evidence": False,
            "original_full_visus_source_resolved": False,
            "public_derivative_partial_corpus_only": True,
            "unrestricted_redistribution_asserted": False,
        },
    }
    canonical = json.dumps(probe, sort_keys=True, separators=(",", ":")).encode()
    import hashlib

    probe["probe_fingerprint_sha256"] = hashlib.sha256(canonical).hexdigest()
    return probe


def test_live_probe_contract_binds_to_committed_evidence() -> None:
    probe = _probe_from_evidence()
    result = validate_visus_public_partial_probe(probe, EVIDENCE)
    assert result["probe_fingerprint_sha256"] == (
        "b1a301151ffae7efefdfccce647f509ec2b7ffe911b88b4979834ca526d1d4b1"
    )


def test_live_probe_drift_fails() -> None:
    probe = _probe_from_evidence()
    probe["participants"][0]["fixation_event_count"] += 1
    body = dict(probe)
    body.pop("probe_fingerprint_sha256")
    import hashlib

    probe["probe_fingerprint_sha256"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_public_partial_probe(probe, EVIDENCE)
