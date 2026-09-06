"""Immutable reviewed evidence for an accessible Hollywood2EM GIN host surface."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError
from .hollywood2_gin_host_metadata import (
    LIVE_RECORD_TYPE,
    LIVE_STATUS,
    REPOSITORY_SLUG,
    evidence_fingerprint,
    probe_fingerprint,
)

EVIDENCE_RECORD_TYPE = "hollywood2-gin-host-metadata-accessible-evidence-v1"
EVIDENCE_STATUS = "reviewed-first-party-host-metadata-no-exact-terms-recovered"
EXPECTED_EVIDENCE_FINGERPRINT_SHA256 = (
    "9e09bfe43a273fbcd8cfe258be547aee18e96b8f0928198d1fb5411555024ced"
)

_BINDING = {
    "repository": "https://gin.g-node.org/ioannis.agtzidis/hollywood2_em.git",
    "commit_sha1": "870fa6d6209c9085260918d61433a0a2c70fd497",
    "authoritative_ground_truth_evidence_fingerprint_sha256":
        "d5375b8768984ef76da02597c55b225aaff4088fd24698c0d53363e2df6b20ea",
    "annotation_provenance_evidence_fingerprint_sha256":
        "a08510e43caca2a8e6d5c85e7b1ad41c9f312247cd9bd8367372f8ecad8aacab",
    "gin_history_evidence_fingerprint_sha256":
        "c7d2f477a66feca3676482ffdabff2b0778196db99e48b86104fe86d0f5bfae1",
    "underlying_source_rights_evidence_fingerprint_sha256":
        "6227045c3cc831b3669b34ca74b955847df4b26fafbf825c9a1b5473e25bc943",
    "author_license_statement_evidence_fingerprint_sha256":
        "b01da719afe18f4eb0103a17d6e8c85f3750ba299050f8026063a9ebb55b1b2e",
}
_DATACITE = (
    ("hollywood2", 27, 27,
     "43a965da66f4b7587727e358a3b6780a84f7144fe808f78d837b7786af2f63d5"),
    ("hollywood2_em", 0, 0,
     "73cad5cc7fa1c12012f82d1963153aa0e7077956287fa8ecd7b92c333ef7a80f"),
    ("ioannis.agtzidis", 1, 1,
     "2e54db785c35e1694f5b45c52febe0d3bc43caf730c3cada46f52b1007797d9e"),
    ("exact_repository_fragment", 0, 0,
     "61a33d8d1b5a659c63bc60cb27fd80af75173a1b2aa0db1b4e35c6533a0fbca1"),
)


def _load(value: Mapping[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    try:
        payload = json.loads(Path(value).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(
            f"Could not load accessible Hollywood2 GIN evidence: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError("Accessible Hollywood2 GIN evidence must be an object.")
    return payload


def _map(record: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = record.get(key)
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(f"Accessible Hollywood2 GIN field {key!r} is missing.")
    return value


def _eq(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BenchmarkIntegrityError(f"Accessible Hollywood2 GIN {label} drifted.")


def _must_false(value: Any, label: str) -> None:
    if value is not False:
        raise BenchmarkIntegrityError(f"Accessible Hollywood2 GIN must not promote {label}.")


def _must_true(value: Any, label: str) -> None:
    if value is not True:
        raise BenchmarkIntegrityError(f"Accessible Hollywood2 GIN must preserve {label}.")


def _validate_rights(record: Mapping[str, Any]) -> None:
    rights = _map(record, "rights_interpretation")
    _must_true(rights.get("gin_host_metadata_inspected"), "reviewed host inspection")
    for key, label in (
        ("reviewed_api_exposes_license_key", "reviewed API license key"),
        ("reviewed_page_exposes_license_keyword", "reviewed page license wording"),
        ("datacite_exact_repository_registration_recovered", "DataCite exact registration"),
        ("host_metadata_license_absence_verified_globally", "global host license absence"),
        ("exact_license_identifier_recovered", "exact license identifier"),
        ("exact_license_text_recovered", "exact license text"),
        ("analysis_use_authorized", "analysis-use authorization"),
        ("raw_data_redistribution_authorized", "redistribution authorization"),
        ("registry_zero_match_is_global_absence_claim", "global registry absence"),
    ):
        _must_false(rights.get(key), label)
    _eq(rights.get("gin_analysis_use_terms_status"), "unresolved_exact_terms", "analysis terms")
    _eq(
        rights.get("gin_raw_data_redistribution_terms_status"),
        "unresolved_exact_terms",
        "redistribution terms",
    )
    _must_true(
        rights.get("author_or_host_clarification_required_for_exact_terms"),
        "author/host clarification requirement",
    )

    boundary = _map(record, "scientific_boundary")
    for key in (
        "participant_identity_mapping_verified",
        "source_audit_ready",
        "participant_disjoint_model_validation_created",
        "cross_dataset_validation_created",
        "independent_human_human_agreement_created",
        "frozen_evidence_performance_claim_created",
    ):
        _must_false(boundary.get(key), key)


def validate_hollywood2_gin_accessible_host_evidence(
    record_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Validate the immutable reviewed first-party GIN host observation."""
    record = _load(record_or_path)
    _eq(record.get("record_type"), EVIDENCE_RECORD_TYPE, "record type")
    _eq(record.get("status"), EVIDENCE_STATUS, "status")
    _eq(record.get("checked_on"), "2026-09-06", "review date")

    binding = _map(record, "canonical_repository_binding")
    for key, expected in _BINDING.items():
        _eq(binding.get(key), expected, f"binding {key}")

    observation = _map(record, "live_observation")
    api = _map(observation, "gin_api")
    expected_api = {
        "http_status": 200,
        "json_object": True,
        "id": 834,
        "name": "hollywood2_em",
        "full_name": REPOSITORY_SLUG,
        "private": False,
        "empty": False,
        "default_branch": "master",
        "license_key_paths": [],
        "response_sha256":
            "02a2939efb657da36980e2367c79e226b3c7e8b52a9dd33468353b97ea0dbd78",
    }
    for key, expected in expected_api.items():
        _eq(api.get(key), expected, f"reviewed API {key}")

    page = _map(observation, "gin_page")
    expected_page = {
        "http_status": 200,
        "contains_license_word": False,
        "contains_licence_word": False,
        "contains_repository_slug": True,
        "response_sha256":
            "41ad0e9f765dce722733b0cf113576b8a0a1fa27025d67f881f34108cd5dfb45",
    }
    for key, expected in expected_page.items():
        _eq(page.get(key), expected, f"reviewed page {key}")

    queries = observation.get("datacite_queries")
    if not isinstance(queries, list) or len(queries) != 4:
        raise BenchmarkIntegrityError("Accessible Hollywood2 GIN DataCite ledger drifted.")
    for query, expected in zip(queries, _DATACITE, strict=True):
        if not isinstance(query, Mapping):
            raise BenchmarkIntegrityError("Accessible Hollywood2 GIN DataCite row is invalid.")
        label, total, returned, response_sha = expected
        _eq(query.get("query_label"), label, "DataCite query label")
        _eq(query.get("reported_total"), total, f"DataCite {label} total")
        _eq(query.get("returned_record_count"), returned, f"DataCite {label} returned")
        _eq(query.get("exact_repository_match_count"), 0, f"DataCite {label} exact match")
        _eq(query.get("response_sha256"), response_sha, f"DataCite {label} SHA-256")

    _validate_rights(record)
    execution = _map(record, "execution")
    expected_execution = {
        "live_probe_record_type": LIVE_RECORD_TYPE,
        "live_probe_fingerprint_sha256":
            "fd66a389c0bfd6b9e225524bd6847eecd5bf21fba56a46c0aa897dac54aeae27",
        "live_probe_json_sha256":
            "70f89cbacb30e874973b7f3af2f9851fd72c2630f2737759f8367e2825b3ad6e",
        "workflow_run_id": 34058146019,
        "probe_head_sha": "7d0ba3fcb5a41c5771e7b64b4fcbf7aa5e27ee71",
        "artifact_id": 9996628764,
        "artifact_zip_sha256":
            "ceb1da449b2407186ecfbae9eff09a3133050dc2b28f4330c54644fc8743a49d",
    }
    for key, expected in expected_execution.items():
        _eq(execution.get(key), expected, f"execution {key}")

    stored = str(record.get("evidence_fingerprint_sha256", ""))
    if stored != evidence_fingerprint(record):
        raise BenchmarkIntegrityError("Accessible Hollywood2 GIN self-fingerprint is invalid.")
    _eq(stored, EXPECTED_EVIDENCE_FINGERPRINT_SHA256, "immutable evidence fingerprint")
    return record


def validate_hollywood2_gin_accessible_host_live_probe(
    probe_or_path: Mapping[str, Any] | str | Path,
    evidence_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Validate fresh semantics against the reviewed accessible-host boundary."""
    validate_hollywood2_gin_accessible_host_evidence(evidence_or_path)
    probe = _load(probe_or_path)
    _eq(probe.get("record_type"), LIVE_RECORD_TYPE, "fresh record type")
    _eq(probe.get("status"), LIVE_STATUS, "fresh status")
    _eq(probe.get("repository"), REPOSITORY_SLUG, "fresh repository")
    _eq(probe.get("probe_fingerprint_sha256"), probe_fingerprint(probe), "fresh fingerprint")

    api = _map(probe, "api")
    page = _map(probe, "page")
    accessible = api.get("http_status") == 200 and api.get("json_object") is True
    if accessible:
        _eq(api.get("full_name"), REPOSITORY_SLUG, "fresh API full name")
        _eq(api.get("license_key_paths"), [], "fresh API license keys")
        _eq(page.get("http_status"), 200, "fresh page HTTP status")
        _must_false(page.get("contains_license_word"), "fresh page license wording")
        _must_false(page.get("contains_licence_word"), "fresh page licence wording")
    else:
        _eq(api.get("http_status"), 403, "fresh unavailable API status")
        _must_false(api.get("json_object"), "fresh unavailable API JSON")
        _eq(api.get("license_key_paths"), [], "fresh unavailable API license keys")
        _eq(page.get("http_status"), 403, "fresh unavailable page status")
        _eq(api.get("sha256"), page.get("sha256"), "fresh unavailable response identity")

    queries = probe.get("datacite_queries")
    if not isinstance(queries, list) or len(queries) != 4:
        raise BenchmarkIntegrityError("Accessible Hollywood2 GIN fresh DataCite ledger drifted.")
    for query in queries:
        if not isinstance(query, Mapping):
            raise BenchmarkIntegrityError(
                "Accessible Hollywood2 GIN fresh DataCite row is invalid."
            )
        _eq(query.get("http_status"), 200, "fresh DataCite HTTP status")
        _must_true(query.get("json_object"), "fresh DataCite JSON")
        _eq(query.get("exact_repository_match_count"), 0, "fresh DataCite exact match")

    rights = _map(probe, "rights_interpretation")
    _eq(rights.get("host_api_metadata_accessible"), accessible, "fresh API accessibility")
    for key in (
        "host_api_exposes_license_key",
        "host_api_exposes_nonempty_license_value",
        "exact_license_identifier_verified",
        "analysis_use_authorized",
        "raw_data_redistribution_authorized",
        "license_inference_from_page_keyword_permitted",
        "registry_zero_match_is_global_absence_claim",
    ):
        _must_false(rights.get(key), key)
    _eq(rights.get("datacite_exact_repository_match_count"), 0, "fresh DataCite matches")

    boundary = _map(probe, "scientific_boundary")
    for key in (
        "participant_identity_mapping_verified",
        "source_audit_ready",
        "participant_disjoint_model_validation_created",
        "cross_dataset_validation_created",
        "frozen_evidence_performance_claim_created",
    ):
        _must_false(boundary.get(key), key)
    return probe
