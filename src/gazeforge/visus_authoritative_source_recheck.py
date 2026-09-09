"""Fail-closed validation for the frozen 2026-09-09 VISUS source recheck.

The record is deliberately non-empirical.  It binds a current institutional
source search to the already-reviewed public derivative evidence while keeping
full-corpus authority, rights, annotation independence, model validation, and
Frozen Evidence authorization unresolved.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError
from .visus_public_event_extension import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256 as EVENT_EXTENSION_FINGERPRINT,
)
from .visus_public_event_extension import validate_visus_public_event_extension_evidence
from .visus_public_partial import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256 as PUBLIC_PARTIAL_FINGERPRINT,
)
from .visus_public_partial import validate_visus_public_partial_evidence
from .visus_source_resolution import validate_visus_source_resolution_record

EXPECTED_RECORD_FINGERPRINT_SHA256 = (
    "97bd19b892032a663b7707235504a7ba886a86d6c3caab4966fa6c5ee96a2571"
)
EXPECTED_CHECKED_ON = "2026-09-09"
EXPECTED_PARTICIPANT_COUNT = 25
EXPECTED_STIMULUS_COUNT = 11

DEFAULT_PUBLIC_PARTIAL_PATH = Path(
    "validation/evidence/visus-public-partial/visus-public-partial-evidence-v1.json"
)
DEFAULT_EVENT_EXTENSION_PATH = Path(
    "validation/evidence/visus-public-event-extension/"
    "visus-public-event-extension-evidence-v1.json"
)

_EXPECTED_MODERN_DARUS = (
    (
        "Dataset for NMF-based Analysis of Mobile Eye-Tracking Data",
        "10.18419/DARUS-4023",
        "CC BY 4.0",
    ),
    (
        'Dataset for "How Deep Is Your Gaze? Leveraging Distance in Image-Based Gaze Analysis"',
        "10.18419/DARUS-4141",
        "CC BY 4.0",
    ),
)

_EXPECTED_PROMOTION_FLAGS = (
    "source_audit_authorized",
    "human_human_agreement_authorized",
    "model_human_validation_authorized",
    "frozen_evidence_authorized",
    "raw_source_redistribution_authorized",
)


def _load(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(f"Could not load VISUS source recheck: {exc}") from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError("VISUS source recheck must be a JSON object.")
    return payload


def _require_mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(f"VISUS source recheck field {key!r} must be an object.")
    return value


def _require_false(value: Any, label: str) -> None:
    if value is not False:
        raise BenchmarkIntegrityError(f"VISUS source recheck must not promote {label}.")


def _require_true(value: Any, label: str) -> None:
    if value is not True:
        raise BenchmarkIntegrityError(f"VISUS source recheck must preserve {label}.")


def _validate_authority_boundary(payload: Mapping[str, Any]) -> None:
    boundary = _require_mapping(payload, "authoritative_source_recheck")
    if boundary.get("full_expected_participant_count") != EXPECTED_PARTICIPANT_COUNT:
        raise BenchmarkIntegrityError("VISUS recheck full participant count must remain 25.")
    if boundary.get("full_expected_stimulus_count") != EXPECTED_STIMULUS_COUNT:
        raise BenchmarkIntegrityError("VISUS recheck full stimulus count must remain 11.")

    _require_false(
        boundary.get("full_authoritative_corpus_recovered"),
        "full authoritative corpus recovery",
    )
    _require_true(
        boundary.get("current_institutional_publication_listing_found"),
        "the current institutional publication listing",
    )
    _require_false(
        boundary.get("current_authoritative_dataset_download_found"),
        "a current authoritative dataset download",
    )
    _require_false(
        boundary.get("matching_darus_record_found"),
        "a matching 2014 benchmark DaRUS record",
    )
    _require_false(
        boundary.get("separate_dataset_doi_found"),
        "a separate 2014 benchmark dataset DOI",
    )
    _require_false(
        boundary.get("explicit_current_dataset_license_found"),
        "an explicit current 2014 benchmark dataset license",
    )
    _require_true(
        boundary.get("modern_darus_license_examples_not_transferable"),
        "the non-transferability of modern DaRUS licenses",
    )
    _require_false(
        boundary.get("partial_derivative_is_authoritative_replacement"),
        "a partial derivative as an authoritative replacement",
    )


def _validate_modern_darus_examples(payload: Mapping[str, Any]) -> None:
    examples = payload.get("modern_darus_examples")
    if not isinstance(examples, list) or len(examples) != len(_EXPECTED_MODERN_DARUS):
        raise BenchmarkIntegrityError("VISUS source recheck must retain two bounded DaRUS examples.")
    observed: list[tuple[str, str, str]] = []
    for row in examples:
        if not isinstance(row, Mapping):
            raise BenchmarkIntegrityError("VISUS DaRUS example must be an object.")
        _require_false(
            row.get("applies_to_2014_benchmark"),
            "a modern DaRUS license onto the 2014 benchmark",
        )
        observed.append(
            (
                str(row.get("title", "")),
                str(row.get("doi", "")),
                str(row.get("license", "")),
            )
        )
    if tuple(observed) != _EXPECTED_MODERN_DARUS:
        raise BenchmarkIntegrityError("VISUS modern DaRUS examples drifted from the frozen recheck.")


def _validate_derivative_bindings(
    payload: Mapping[str, Any],
    public_partial_path: str | Path,
    event_extension_path: str | Path,
) -> None:
    # Revalidate the actual repository evidence, not merely copied hash strings.
    partial = validate_visus_public_partial_evidence(public_partial_path)
    extension = validate_visus_public_event_extension_evidence(event_extension_path)
    if partial.get("evidence_fingerprint_sha256") != PUBLIC_PARTIAL_FINGERPRINT:
        raise BenchmarkIntegrityError("VISUS public-partial evidence fingerprint drifted.")
    if extension.get("evidence_fingerprint_sha256") != EVENT_EXTENSION_FINGERPRINT:
        raise BenchmarkIntegrityError("VISUS event-extension evidence fingerprint drifted.")

    bindings = payload.get("reviewed_derivative_evidence")
    if not isinstance(bindings, list) or len(bindings) != 2:
        raise BenchmarkIntegrityError("VISUS source recheck must bind exactly two derivative records.")

    expected = {
        "visus-public-partial-evidence-v1": PUBLIC_PARTIAL_FINGERPRINT,
        "visus-public-event-extension-evidence-v1": EVENT_EXTENSION_FINGERPRINT,
    }
    observed: dict[str, str] = {}
    for row in bindings:
        if not isinstance(row, Mapping):
            raise BenchmarkIntegrityError("VISUS derivative binding must be an object.")
        record_type = str(row.get("record_type", ""))
        fingerprint = str(row.get("evidence_fingerprint_sha256", ""))
        observed[record_type] = fingerprint
        _require_false(row.get("full_visus_recovered"), "full VISUS recovery from derivatives")
        _require_false(row.get("authoritative_replacement"), "derivative source authority")
    if observed != expected:
        raise BenchmarkIntegrityError("VISUS derivative evidence bindings drifted from reviewed records.")


def _validate_promotion_boundary(payload: Mapping[str, Any]) -> None:
    promotion = _require_mapping(payload, "promotion_boundary")
    if set(promotion) != set(_EXPECTED_PROMOTION_FLAGS):
        raise BenchmarkIntegrityError("VISUS source-recheck promotion boundary fields drifted.")
    for key in _EXPECTED_PROMOTION_FLAGS:
        _require_false(promotion.get(key), key.replace("_", " "))


def validate_visus_authoritative_source_recheck(
    record_path: str | Path,
    *,
    public_partial_path: str | Path = DEFAULT_PUBLIC_PARTIAL_PATH,
    event_extension_path: str | Path = DEFAULT_EVENT_EXTENSION_PATH,
) -> dict[str, Any]:
    """Validate the frozen 2026-09-09 VISUS authoritative-source recheck.

    The generic source-resolution validator is run first.  This layer then
    freezes the dated current-source findings and binds the two reviewed public
    derivative records.  No field in this record can authorize empirical work.
    """

    generic = validate_visus_source_resolution_record(record_path)
    payload = _load(record_path)

    if generic["checked_on"] != EXPECTED_CHECKED_ON:
        raise BenchmarkIntegrityError("VISUS authoritative-source recheck date drifted.")
    if generic["record_fingerprint_sha256"] != EXPECTED_RECORD_FINGERPRINT_SHA256:
        raise BenchmarkIntegrityError("VISUS authoritative-source recheck fingerprint drifted.")

    _validate_authority_boundary(payload)
    _validate_modern_darus_examples(payload)
    _validate_derivative_bindings(payload, public_partial_path, event_extension_path)
    _validate_promotion_boundary(payload)

    annotation = _require_mapping(payload, "annotation_independence")
    _require_false(
        annotation.get("independent_annotation_streams_verified"),
        "independent annotation streams",
    )
    _require_false(annotation.get("human_human_agreement_ready"), "human-human agreement")

    return {
        "record_type": generic["record_type"],
        "checked_on": generic["checked_on"],
        "status": generic["status"],
        "record_fingerprint_sha256": generic["record_fingerprint_sha256"],
        "full_authoritative_corpus_recovered": False,
        "current_authoritative_dataset_download_found": False,
        "explicit_current_dataset_license_found": False,
        "source_audit_authorized": False,
        "human_human_agreement_authorized": False,
        "model_human_validation_authorized": False,
        "frozen_evidence_authorized": False,
        "raw_source_redistribution_authorized": False,
        "public_partial_fingerprint_sha256": PUBLIC_PARTIAL_FINGERPRINT,
        "event_extension_fingerprint_sha256": EVENT_EXTENSION_FINGERPRINT,
    }
