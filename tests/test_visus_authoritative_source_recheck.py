from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.visus_authoritative_source_recheck import (
    EVENT_EXTENSION_FINGERPRINT,
    EXPECTED_RECORD_FINGERPRINT_SHA256,
    PUBLIC_PARTIAL_FINGERPRINT,
    validate_visus_authoritative_source_recheck,
)

_RECORD = Path("validation/protocols/visus-source-resolution-2026-09-09.json")
_PARTIAL = Path(
    "validation/evidence/visus-public-partial/visus-public-partial-evidence-v1.json"
)
_EXTENSION = Path(
    "validation/evidence/visus-public-event-extension/"
    "visus-public-event-extension-evidence-v1.json"
)


def _load(path: Path = _RECORD) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _refingerprint(payload: dict[str, Any]) -> None:
    body = dict(payload)
    body.pop("record_fingerprint_sha256", None)
    encoded = json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    payload["record_fingerprint_sha256"] = hashlib.sha256(encoded).hexdigest()


def _write_mutated(
    tmp_path: Path,
    path: tuple[str | int, ...],
    value: Any,
) -> Path:
    payload = copy.deepcopy(_load())
    cursor: Any = payload
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    _refingerprint(payload)
    target = tmp_path / "mutated-visus-source-recheck.json"
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def test_frozen_visus_authoritative_source_recheck_validates() -> None:
    summary = validate_visus_authoritative_source_recheck(_RECORD)
    assert summary["record_fingerprint_sha256"] == EXPECTED_RECORD_FINGERPRINT_SHA256
    assert summary["status"] == "current_authoritative_distribution_unresolved"
    assert summary["full_authoritative_corpus_recovered"] is False
    assert summary["current_authoritative_dataset_download_found"] is False
    assert summary["explicit_current_dataset_license_found"] is False
    assert summary["source_audit_authorized"] is False
    assert summary["human_human_agreement_authorized"] is False
    assert summary["model_human_validation_authorized"] is False
    assert summary["frozen_evidence_authorized"] is False
    assert summary["raw_source_redistribution_authorized"] is False
    assert summary["public_partial_fingerprint_sha256"] == PUBLIC_PARTIAL_FINGERPRINT
    assert summary["event_extension_fingerprint_sha256"] == EVENT_EXTENSION_FINGERPRINT


def test_record_fingerprint_matches_frozen_value() -> None:
    payload = _load()
    stored = payload.pop("record_fingerprint_sha256")
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    assert hashlib.sha256(encoded).hexdigest() == stored == EXPECTED_RECORD_FINGERPRINT_SHA256


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("authoritative_source_recheck", "full_authoritative_corpus_recovered"), True),
        (("authoritative_source_recheck", "current_authoritative_dataset_download_found"), True),
        (("authoritative_source_recheck", "matching_darus_record_found"), True),
        (("authoritative_source_recheck", "separate_dataset_doi_found"), True),
        (("authoritative_source_recheck", "explicit_current_dataset_license_found"), True),
        (
            (
                "authoritative_source_recheck",
                "modern_darus_license_examples_not_transferable",
            ),
            False,
        ),
        (("authoritative_source_recheck", "partial_derivative_is_authoritative_replacement"), True),
        (("modern_darus_examples", 0, "applies_to_2014_benchmark"), True),
        (("modern_darus_examples", 1, "applies_to_2014_benchmark"), True),
        (("reviewed_derivative_evidence", 0, "full_visus_recovered"), True),
        (("reviewed_derivative_evidence", 0, "authoritative_replacement"), True),
        (("reviewed_derivative_evidence", 1, "full_visus_recovered"), True),
        (("reviewed_derivative_evidence", 1, "authoritative_replacement"), True),
        (
            ("reviewed_derivative_evidence", 0, "evidence_fingerprint_sha256"),
            "0" * 64,
        ),
        (("promotion_boundary", "source_audit_authorized"), True),
        (("promotion_boundary", "human_human_agreement_authorized"), True),
        (("promotion_boundary", "model_human_validation_authorized"), True),
        (("promotion_boundary", "frozen_evidence_authorized"), True),
        (("promotion_boundary", "raw_source_redistribution_authorized"), True),
        (("annotation_independence", "independent_annotation_streams_verified"), True),
        (("annotation_independence", "human_human_agreement_ready"), True),
        (("rights", "analysis_use_terms_status"), "verified"),
        (("rights", "raw_data_redistribution_terms_status"), "verified"),
        (("rights", "license_inference_permitted"), True),
        (("rights", "paper_copyright_notice_is_dataset_license"), True),
        (("source_audit_ready",), True),
        (("empirical_evidence_created",), True),
        (("current_authoritative_download_found",), True),
    ],
)
def test_refingerprinted_promotions_are_rejected(
    tmp_path: Path,
    path: tuple[str | int, ...],
    value: Any,
) -> None:
    mutated = _write_mutated(tmp_path, path, value)
    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_authoritative_source_recheck(mutated)


def test_partial_derivative_body_is_revalidated(tmp_path: Path) -> None:
    payload = json.loads(_PARTIAL.read_text(encoding="utf-8"))
    payload["coverage"]["full_visus_recovered"] = True
    body = dict(payload)
    body.pop("evidence_fingerprint_sha256", None)
    payload["evidence_fingerprint_sha256"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    target = tmp_path / "partial.json"
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_authoritative_source_recheck(_RECORD, public_partial_path=target)


def test_event_extension_body_is_revalidated(tmp_path: Path) -> None:
    payload = json.loads(_EXTENSION.read_text(encoding="utf-8"))
    payload["scientific_boundary"]["original_full_visus_source_resolved"] = True
    body = dict(payload)
    body.pop("evidence_fingerprint_sha256", None)
    payload["evidence_fingerprint_sha256"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    target = tmp_path / "extension.json"
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_authoritative_source_recheck(_RECORD, event_extension_path=target)
