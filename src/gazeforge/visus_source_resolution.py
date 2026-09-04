"""Validation for conservative VISUS source-resolution status checkpoints."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError

_RECORD_TYPE = "source-resolution-status-v1"
_DATASET = "VISUS dynamic-video eye-tracking benchmark"
_RIGHTS_STATES = {"unresolved", "verified", "not_permitted"}
_HEX = set("0123456789abcdef")


def _fingerprint(payload: Mapping[str, Any]) -> str:
    canonical = dict(payload)
    canonical.pop("record_fingerprint_sha256", None)
    encoded = json.dumps(
        canonical,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _require_bool(payload: Mapping[str, Any], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise BenchmarkIntegrityError(f"VISUS source-resolution field {key!r} must be boolean.")
    return value


def _require_mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(f"VISUS source-resolution field {key!r} must be an object.")
    return value


@dataclass(frozen=True, slots=True)
class VisusSourceResolutionRecord:
    """Compact identity of one validated source-resolution checkpoint."""

    path: Path
    checked_on: str
    status: str
    record_fingerprint_sha256: str
    current_authoritative_download_found: bool
    source_audit_ready: bool
    empirical_evidence_created: bool
    analysis_use_terms_status: str
    raw_data_redistribution_terms_status: str
    independent_annotation_streams_verified: bool
    human_human_agreement_ready: bool


def validate_visus_source_resolution_record(path: str | Path) -> dict[str, Any]:
    """Validate one non-empirical VISUS source-resolution checkpoint.

    The validator is deliberately narrower than the VISUS source audit. It checks that a status
    checkpoint cannot silently turn historical availability, a publication copyright notice, or a
    two-contributor curation process into current source authority, dataset rights, independent
    annotation streams, or empirical evidence.
    """
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise BenchmarkIntegrityError("VISUS source-resolution checkpoint must be a JSON object.")

    if payload.get("record_type") != _RECORD_TYPE:
        raise BenchmarkIntegrityError(
            f"VISUS source-resolution record_type must be {_RECORD_TYPE!r}."
        )
    if payload.get("dataset") != _DATASET:
        raise BenchmarkIntegrityError(f"VISUS source-resolution dataset must be {_DATASET!r}.")

    checked_on = str(payload.get("checked_on", "")).strip()
    try:
        date.fromisoformat(checked_on)
    except ValueError as exc:
        raise BenchmarkIntegrityError(
            "VISUS source-resolution checked_on must be an ISO calendar date."
        ) from exc

    status = str(payload.get("status", "")).strip()
    if not status:
        raise BenchmarkIntegrityError("VISUS source-resolution status cannot be empty.")

    empirical = _require_bool(payload, "empirical_evidence_created")
    audit_ready = _require_bool(payload, "source_audit_ready")
    current_download = _require_bool(payload, "current_authoritative_download_found")

    publication = _require_mapping(payload, "authoritative_publication")
    if publication.get("doi") != "10.1145/2669557.2669558":
        raise BenchmarkIntegrityError("VISUS source-resolution publication DOI is unexpected.")
    if publication.get("publication_states_dataset_license") is not False:
        raise BenchmarkIntegrityError(
            "The VISUS benchmark paper must not be represented as stating a dataset license."
        )

    rights = _require_mapping(payload, "rights")
    analysis_rights = str(rights.get("analysis_use_terms_status", "")).strip()
    redistribution_rights = str(
        rights.get("raw_data_redistribution_terms_status", "")
    ).strip()
    if analysis_rights not in _RIGHTS_STATES or redistribution_rights not in _RIGHTS_STATES:
        raise BenchmarkIntegrityError(
            "VISUS source-resolution rights statuses must be unresolved, verified, "
            "or not_permitted."
        )
    if rights.get("paper_copyright_notice_is_dataset_license") is not False:
        raise BenchmarkIntegrityError(
            "A publication copyright notice cannot be promoted into a VISUS dataset license."
        )
    if rights.get("license_inference_permitted") is not False:
        raise BenchmarkIntegrityError(
            "VISUS source-resolution checkpoints cannot infer a dataset license."
        )

    annotation = _require_mapping(payload, "annotation_independence")
    independent = annotation.get("independent_annotation_streams_verified")
    human_ready = annotation.get("human_human_agreement_ready")
    if not isinstance(independent, bool) or not isinstance(human_ready, bool):
        raise BenchmarkIntegrityError(
            "VISUS annotation-independence flags must be boolean."
        )
    if human_ready and not independent:
        raise BenchmarkIntegrityError(
            "VISUS human-human agreement cannot be ready without verified independent streams."
        )

    if status == "current_authoritative_distribution_unresolved":
        if current_download or audit_ready or empirical:
            raise BenchmarkIntegrityError(
                "An unresolved VISUS distribution cannot be current-download, source-audit-ready, "
                "or empirical."
            )
        if analysis_rights != "unresolved" or redistribution_rights != "unresolved":
            raise BenchmarkIntegrityError(
                "The unresolved VISUS checkpoint must keep analysis and redistribution terms "
                "separately unresolved."
            )
        if independent or human_ready:
            raise BenchmarkIntegrityError(
                "The unresolved VISUS checkpoint cannot verify independent annotation streams."
            )

    if audit_ready and not current_download:
        raise BenchmarkIntegrityError(
            "VISUS source_audit_ready requires a current authoritative copy to have been found."
        )
    if empirical and not audit_ready:
        raise BenchmarkIntegrityError(
            "VISUS empirical_evidence_created cannot precede source-audit readiness."
        )

    claim_limits = payload.get("claim_limits")
    if not isinstance(claim_limits, list) or not claim_limits or not all(
        isinstance(item, str) and item.strip() for item in claim_limits
    ):
        raise BenchmarkIntegrityError(
            "VISUS source-resolution checkpoints require explicit non-empty claim limits."
        )

    fingerprint = _fingerprint(payload)
    stored = payload.get("record_fingerprint_sha256")
    if stored is not None:
        stored_text = str(stored).strip().lower()
        if len(stored_text) != 64 or any(character not in _HEX for character in stored_text):
            raise BenchmarkIntegrityError(
                "VISUS source-resolution record fingerprint must contain 64 hex digits."
            )
        if stored_text != fingerprint:
            raise BenchmarkIntegrityError(
                "VISUS source-resolution record fingerprint does not match its content."
            )

    return {
        "record_type": _RECORD_TYPE,
        "dataset": _DATASET,
        "checked_on": checked_on,
        "status": status,
        "record_fingerprint_sha256": fingerprint,
        "current_authoritative_download_found": current_download,
        "source_audit_ready": audit_ready,
        "empirical_evidence_created": empirical,
        "rights": {
            "analysis_use_terms_status": analysis_rights,
            "raw_data_redistribution_terms_status": redistribution_rights,
        },
        "annotation_independence": {
            "independent_annotation_streams_verified": independent,
            "human_human_agreement_ready": human_ready,
        },
        "claim_limits": list(claim_limits),
    }


def load_visus_source_resolution_record(path: str | Path) -> VisusSourceResolutionRecord:
    """Return a compact typed checkpoint after strict validation."""
    source = Path(path)
    summary = validate_visus_source_resolution_record(source)
    return VisusSourceResolutionRecord(
        path=source,
        checked_on=str(summary["checked_on"]),
        status=str(summary["status"]),
        record_fingerprint_sha256=str(summary["record_fingerprint_sha256"]),
        current_authoritative_download_found=bool(
            summary["current_authoritative_download_found"]
        ),
        source_audit_ready=bool(summary["source_audit_ready"]),
        empirical_evidence_created=bool(summary["empirical_evidence_created"]),
        analysis_use_terms_status=str(summary["rights"]["analysis_use_terms_status"]),
        raw_data_redistribution_terms_status=str(
            summary["rights"]["raw_data_redistribution_terms_status"]
        ),
        independent_annotation_streams_verified=bool(
            summary["annotation_independence"]["independent_annotation_streams_verified"]
        ),
        human_human_agreement_ready=bool(
            summary["annotation_independence"]["human_human_agreement_ready"]
        ),
    )
