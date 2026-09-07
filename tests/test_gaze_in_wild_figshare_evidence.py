from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_figshare_evidence import (
    evidence_fingerprint,
    validate_gaze_in_wild_figshare_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (
    ROOT
    / "validation/evidence/gaze-in-wild/gaze-in-wild-figshare-distribution-rights-evidence-v1.json"
)
RAW = ROOT / "validation/evidence/gaze-in-wild/gaze-in-wild-figshare-public-metadata-raw-v1.json"
SUMMARY = (
    ROOT / "validation/evidence/gaze-in-wild/gaze-in-wild-figshare-public-metadata-summary-v1.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _fingerprint(record: dict, stored_key: str) -> str:
    body = copy.deepcopy(record)
    body.pop(stored_key, None)
    payload = json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _refresh_evidence(record: dict) -> dict:
    record["evidence_fingerprint_sha256"] = evidence_fingerprint(record)
    return record


def _refresh_raw(record: dict) -> dict:
    record["probe_fingerprint_sha256"] = _fingerprint(record, "probe_fingerprint_sha256")
    return record


def _refresh_summary(record: dict) -> dict:
    record["summary_fingerprint_sha256"] = _fingerprint(record, "summary_fingerprint_sha256")
    return record


def test_reviewed_figshare_evidence_validates() -> None:
    result = validate_gaze_in_wild_figshare_evidence(EVIDENCE, RAW, SUMMARY)
    assert result.deposit_rights_resolved is True
    assert result.analysis_use_permitted is True
    assert result.redistribution_permitted is True
    assert result.exact_file_bytes_verified is False
    assert result.quarantine_exit_authorized is False


def test_reviewed_license_cannot_drift_even_with_rehashed_record() -> None:
    record = _load(EVIDENCE)
    record["rights_boundary"]["verified_license_name"] = "MIT"
    _refresh_evidence(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_figshare_evidence(record, RAW, SUMMARY)


def test_live_item_license_cannot_drift_even_with_rehashed_probe() -> None:
    raw = _load(RAW)
    raw["items"][0]["license"]["name"] = "CC0"
    _refresh_raw(raw)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_figshare_evidence(EVIDENCE, raw, SUMMARY)


def test_link_only_file_is_rejected() -> None:
    raw = _load(RAW)
    raw["items"][0]["files"][0]["is_link_only"] = True
    raw["items"][0]["manifest_sha256"] = _fingerprint({"files": raw["items"][0]["files"]}, "unused")
    _refresh_raw(raw)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_figshare_evidence(EVIDENCE, raw, SUMMARY)


def test_mismatched_file_md5_is_rejected() -> None:
    raw = _load(RAW)
    raw["items"][0]["files"][0]["computed_md5"] = "0" * 32
    raw["items"][0]["manifest_sha256"] = hashlib.sha256(
        json.dumps(
            raw["items"][0]["files"],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    _refresh_raw(raw)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_figshare_evidence(EVIDENCE, raw, SUMMARY)


def test_pridx_4_manifest_mismatch_cannot_be_erased() -> None:
    summary = _load(SUMMARY)
    summary["derived_manifest_structure"]["processdata_participant_ids"].remove(4)
    _refresh_summary(summary)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_figshare_evidence(EVIDENCE, RAW, summary)


def test_participant_mapping_cannot_be_promoted() -> None:
    record = _load(EVIDENCE)
    record["manifest_structure"]["published_participant_to_distribution_mapping_complete"] = True
    _refresh_evidence(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_figshare_evidence(record, RAW, SUMMARY)


def test_cleaned_data_cannot_be_promoted_to_original() -> None:
    record = _load(EVIDENCE)
    record["deposits"]["ProcessData_cleaned"]["is_original_publication_processed_distribution"] = (
        True
    )
    _refresh_evidence(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_figshare_evidence(record, RAW, SUMMARY)


def test_human_agreement_cannot_be_created_by_metadata() -> None:
    record = _load(EVIDENCE)
    record["scientific_boundary"]["human_human_agreement_created"] = True
    _refresh_evidence(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_figshare_evidence(record, RAW, SUMMARY)


def test_quarantine_exit_cannot_be_promoted_by_rights_metadata() -> None:
    record = _load(EVIDENCE)
    record["scientific_boundary"]["quarantine_exit_authorized"] = True
    _refresh_evidence(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_figshare_evidence(record, RAW, SUMMARY)
