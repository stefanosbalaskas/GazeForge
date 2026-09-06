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
EXPECTED_LIVE_PROBE_FINGERPRINT_SHA256 = (
    "fd66a389c0bfd6b9e225524bd6847eecd5bf21fba56a46c0aa897dac54aeae27"
)
EXPECTED_LIVE_PROBE_JSON_SHA256 = (
    "70f89cbacb30e874973b7f3af2f9851fd72c2630f2737759f8367e2825b3ad6e"
)

_BINDING = {
    "repository": "https://gin.g-node.org/ioannis.agtzidis/hollywood2_em.git",
    "commit_sha1": "870fa6d6209c9085260918d61433a0a2c70fd497",
    "authoritative_ground_truth_evidence_fingerprint_sha256": (
        "d5375b8768984ef76da02597c55b225aaff4088fd24698c0d53363e2df6b20ea"
    ),
    "annotation_provenance_evidence_fingerprint_sha256": (
        "a08510e43caca2a8e6d5c85e7b1ad41c9f312247cd9bd8367372f8ecad8aacab"
    ),
    "gin_history_evidence_fingerprint_sha256": (
        "c7d2f477a66feca3676482ffdabff2b0778196db99e48b86104fe86d0f5bfae1"
    ),
    "underlying_source_rights_evidence_fingerprint_sha256": (
        "6227045c3cc831b3669b34ca74b955847df4b26fafbf825c9a1b5473e25bc943"
    ),
    "author_license_statement_evidence_fingerprint_sha256": (
        "b01da719afe18f4eb0103a17d6e8c85f3750ba299050f8026063a9ebb55b1b2e"
    ),
}
_DATACITE = (
    (
        "hollywood2",
        27,
        27,
        "43a965da66f4b7587727e358a3b6780a84f7144fe808f78d837b7786af2f63d5",
    ),
    (
        "hollywood2_em",
        0,
        0,
        "73cad5cc7fa1c12012f82d1963153aa0e7077956287fa8ecd7b92c333ef7a80f",
    ),
    (
        "ioannis.agtzidis",
        1,
        1,
        "2e54db785c35e1694f5b45c52febe0d3bc43caf730c3cada46f52b1007797d9e",
    ),
    (
        "exact_repository_fragment",
        0,
        0,
        "61a33d8d1b5a659c63bc60cb27fd80af75173a1b2aa0db1b4e35c6533a0fbca1",
    ),
)


def _load(record_or_path: Mapping[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(record_or_path, Mapping):
        return dict(record_or_path)
    try:
        payload = json.loads(Path(record_or_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(
            f"Could not load accessible Hollywood2 GIN host evidence: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError("Accessible Hollywood2 GIN host evidence must be an object.")
    return payload


def _mapping(record: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = record.get(key)
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(f"Accessible Hollywood2 GIN field {key!r} is missing.")
    return value


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BenchmarkIntegrityError(f"Accessible Hollywood2 GIN {label} drifted.")


def _true(value: Any, label: str) -> None:
    if value is not True:
        raise BenchmarkIntegrityError(f"Accessible Hollywood2 GIN must preserve {label}.")


def _false(value: Any, label: str) -> None:
    if value is not False:
        raise BenchmarkIntegrityError(f"Accessible Hollywood2 GIN must not promote {label}.")


def _validate_boundaries(record: Mapping[str, Any]) -> None:
    rights = _mapping(record, "rights_interpretation")
    _true(rights.get("gin_host_metadata_inspected"), "reviewed host inspection")
    _false(rights.get("reviewed_api_exposes_license_key"), "reviewed API license key")
    _false(rights.get("reviewed_page_exposes_license_keyword"), "reviewed page license wording")
    _false(
        rights.get("datacite_exact_repository_registration_recovered"),
        "DataCite exact repository registration",
    )
    _false(
        rights.get("host_metadata_license_absence_verified_globally"),
        "global host license absence",
    )
    _false(rights.get("exact_license_identifier_recovered"), "exact license identifier")
    _false(rights.get("exact_license_text_recovered"), "exact license text")
    _equal(rights.get("gin_analysis_use_terms_status"), "unresolved_exact_terms", "analysis terms")
    _equal(
        rights.get("gin_raw_data_redistribution_terms_status"),
        "unresolved_exact_terms",
        "redistribution terms",
    )
    _false(rights.get("analysis_use_authorized"), "analysis-use authorization")
    _false(rights.get("raw_data_redistribution_authorized"), "redistribution authorization")
    _false(rights.get("registry_zero_match_is_global_absence_claim"), "global registry absence")
    _true(
        rights.get("author_or_host_clarification_required_for_exact_terms"),
        "author/host clarification requirement",
    )

    boundary = _mapping(record, "scientific_boundary")
    for key, label in (
        ("participant_identity_mapping_verified", "participant mapping"),
        ("source_audit_ready", "source-audit readiness"),
        ("participant_disjoint_model_validation_created", "participant-disjoint validation"),
        ("cross_dataset_validation_created", "cross-dataset validation"),
        ("independent_human_human_agreement_created", "independent human-human agreement"),
        ("frozen_evidence_performance_claim_created", "new performance Frozen Evidence"),
    ):
        _false(boundary.get(key), label)


def validate_hollywood2_gin_accessible_host_evidence(
    record_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Validate the immutable reviewed first-party GIN host observation."""
    record = _load(record_or_path)
    _equal(record.get("record_type"), EVIDENCE_RECORD_TYPE, "record type")
    _equal(record.get("status"), EVIDENCE_STATUS, "status")
    _equal(record.get("checked_on"), "2026-09-06", "review date")

    binding = _mapping(record, "canonical_repository_binding")
    for key, expected in _BINDING.items():
        _equal(binding.get(key), expected, f"binding {key}")

    observation = _mapping(record, "live_observation")
    api = _mapping(observation, "gin_api")
    _equal(api.get("http_status"), 200, "reviewed API HTTP status")
    _true(api.get("json_object"), "reviewed API JSON object")
    _equal(api.get("id"), 834, "reviewed API repository id")
    _equal(api.get("name"), "hollywood2_em", "reviewed API repository name")
    _equal(api.get("full_name"), REPOSITORY_SLUG, "reviewed API repository full name")
    _false(api.get("private"), "reviewed API private flag")
    _false(api.get("empty"), "reviewed API empty flag")
    _equal(api.get("default_branch"), "master", "reviewed API default branch")
    _equal(api.get("license_key_paths"), [], "reviewed API license key paths")
    _equal(
        api.get("response_sha256"),
        "02a2939efb657da36980e2367c79e226b3c7e8b52a9dd33468353b97ea0dbd78",
        "reviewed API response SHA-256",
    )

    page = _mapping(observation, "gin_page")
    _equal(page.get("http_status"), 200, "reviewed page HTTP status")
    _false(page.get("contains_license_word"), "reviewed page license keyword")
    _false(page.get("contains_licence_word"), "reviewed page licence keyword")
    _true(page.get("contains_repository_slug"), "reviewed page repository slug")
    _equal(
        page.get("response_sha256"),
        "41ad0e9f765dce722733b0cf113576b8a0a1fa27025d67f881f34108cd5dfb45",
        "reviewed page response SHA-256",
    )

    queries = observation.get("datacite_queries")
    if not isinstance(queries, list) or len(queries) != len(_DATACITE):
        raise BenchmarkIntegrityError("Accessible Hollywood2 GIN DataCite ledger drifted.")
    for query, expected in zip(queries, _DATACITE, strict=True):
        if not isinstance(query, Mapping):
            raise BenchmarkIntegrityError("Accessible Hollywood2 GIN DataCite row is invalid.")
        label, total, returned, response_sha = expected
        _equal(query.get("query_label"), label, "DataCite query label")
        _equal(query.get("reported_total"), total, f"DataCite {label} total")
        _equal(query.get("returned_record_count"), returned, f"DataCite {label} returned count")
        _equal(query.get("exact_repository_match_count"), 0, f"DataCite {label} exact match")
        _equal(query.get("response_sha256"), response_sha, f"DataCite {label} response SHA-256")

    _validate_boundaries(record)

    execution = _mapping(record, "execution")
    _equal(execution.get("live_probe_record_type"), LIVE_RECORD_TYPE, "live probe record type")
    _equal(
        execution.get("live_probe_fingerprint_sha256"),
        EXPECTED_LIVE_PROBE_FINGERPRINT_SHA256,
        "live probe fingerprint",
    )
    _equal(
        execution.get("live_probe_json_sha256"),
        EXPECTED_LIVE_PROBE_JSON_SHA256,
        "live probe JSON SHA-256",
    )
    _equal(execution.get("workflow_run_id"), 34058146019, "workflow run id")
    _equal(
        execution.get("probe_head_sha"),
        "7d0ba3fcb5a41c5771e7b64b4fcbf7aa5e27ee71",
        "probe head SHA",
    )
    _equal(execution.get("artifact_id"), 9996628764, "artifact id")
    _equal(
        execution.get("artifact_zip_sha256"),
        "ceb1da449b2407186ecfbae9eff09a3133050dc2b28f4330c54644fc8743a49d",
        "artifact ZIP SHA-256",
    )

    stored = str(record.get("evidence_fingerprint_sha256", ""))
    if stored != evidence_fingerprint(record):
        raise BenchmarkIntegrityError(
            "Accessible Hollywood2 GIN evidence self-fingerprint is invalid."
        )
    if stored != EXPECTED_EVIDENCE_FINGERPRINT_SHA256:
        raise BenchmarkIntegrityError("Accessible Hollywood2 GIN immutable v1 fingerprint drifted.")
    return record


def validate_hollywood2_gin_accessible_host_live_probe(
    probe_or_path: Mapping[str, Any] | str | Path,
    evidence_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Validate fresh semantics against the reviewed accessible-host rights boundary."""
    validate_hollywood2_gin_accessible_host_evidence(evidence_or_path)
    probe = _load(probe_or_path)
    _equal(probe.get("record_type"), LIVE_RECORD_TYPE, "fresh record type")
    _equal(probe.get("status"), LIVE_STATUS, "fresh status")
    _equal(probe.get("repository"), REPOSITORY_SLUG, "fresh repository")
    stored = str(probe.get("probe_fingerprint_sha256", ""))
    if stored != probe_fingerprint(probe):
        raise BenchmarkIntegrityError("Accessible Hollywood2 GIN fresh fingerprint is invalid.")

    api = _mapping(probe, "api")
    page = _mapping(probe, "page")
    api_accessible = api.get("http_status") == 200 and api.get("json_object") is True
    if api_accessible:
        _equal(api.get("full_name"), REPOSITORY_SLUG, "fresh API repository full name")
        _equal(api.get("license_key_paths"), [], "fresh API license key paths")
        _equal(page.get("http_status"), 200, "fresh page HTTP status")
        _false(page.get("contains_license_word"), "fresh page license keyword")
        _false(page.get("contains_licence_word"), "fresh page licence keyword")
    else:
        _equal(api.get("http_status"), 403, "fresh unavailable API HTTP status")
        _false(api.get("json_object"), "fresh unavailable API JSON object")
        _equal(api.get("license_key_paths"), [], "fresh unavailable API license paths")
        _equal(page.get("http_status"), 403, "fresh unavailable page HTTP status")
        _equal(api.get("sha256"), page.get("sha256"), "fresh unavailable response identity")

    queries = probe.get("datacite_queries")
    if not isinstance(queries, list) or len(queries) != 4:
        raise BenchmarkIntegrityError("Accessible Hollywood2 GIN fresh DataCite ledger drifted.")
    for query in queries:
        if not isinstance(query, Mapping):
            raise BenchmarkIntegrityError("Accessible Hollywood2 GIN fresh DataCite row is invalid.")
        _equal(query.get("http_status"), 200, "fresh DataCite HTTP status")
        _true(query.get("json_object"), "fresh DataCite JSON object")
        _equal(query.get("exact_repository_match_count"), 0, "fresh DataCite exact match count")

    rights = _mapping(probe, "rights_interpretation")
    _equal(rights.get("host_api_metadata_accessible"), api_accessible, "fresh API accessibility")
    _false(rights.get("host_api_exposes_license_key"), "fresh API license key")
    _false(rights.get("host_api_exposes_nonempty_license_value"), "fresh API license value")
    _equal(rights.get("datacite_exact_repository_match_count"), 0, "fresh DataCite exact matches")
    _false(rights.get("exact_license_identifier_verified"), "fresh exact license verification")
    _false(rights.get("analysis_use_authorized"), "fresh analysis-use authorization")
    _false(rights.get("raw_data_redistribution_authorized"), "fresh redistribution authorization")
    _false(
        rights.get("license_inference_from_page_keyword_permitted"),
        "fresh page-keyword inference",
    )
    _false(rights.get("registry_zero_match_is_global_absence_claim"), "fresh global absence claim")

    boundary = _mapping(probe, "scientific_boundary")
    for key, label in (
        ("participant_identity_mapping_verified", "fresh participant mapping"),
        ("source_audit_ready", "fresh source-audit readiness"),
        ("participant_disjoint_model_validation_created", "fresh participant validation"),
        ("cross_dataset_validation_created", "fresh cross-dataset validation"),
        ("frozen_evidence_performance_claim_created", "fresh performance Frozen Evidence"),
    ):
        _false(boundary.get(key), label)
    return probe
