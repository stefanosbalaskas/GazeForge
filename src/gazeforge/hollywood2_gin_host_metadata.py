"""Conservative helpers for public Hollywood2EM host and registry metadata."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError

REPO_PAGE = "https://gin.g-node.org/ioannis.agtzidis/hollywood2_em"
REPO_API = "https://gin.g-node.org/api/v1/repos/ioannis.agtzidis/hollywood2_em"
REPO_GIT = f"{REPO_PAGE}.git"
REPOSITORY_SLUG = "ioannis.agtzidis/hollywood2_em"
REPOSITORY_URL_MARKERS = (
    "https://gin.g-node.org/ioannis.agtzidis/hollywood2_em",
    "http://gin.g-node.org/ioannis.agtzidis/hollywood2_em",
    "https://web.gin.g-node.org/ioannis.agtzidis/hollywood2_em",
    "http://web.gin.g-node.org/ioannis.agtzidis/hollywood2_em",
)
DATACITE_QUERY_URLS = (
    "https://api.datacite.org/dois?query=hollywood2&page%5Bsize%5D=100",
    "https://api.datacite.org/dois?query=hollywood2_em&page%5Bsize%5D=100",
    "https://api.datacite.org/dois?query=ioannis.agtzidis&page%5Bsize%5D=100",
    (
        "https://api.datacite.org/dois?query="
        "gin.g-node.org%2Fioannis.agtzidis%2Fhollywood2_em&page%5Bsize%5D=100"
    ),
)

LIVE_RECORD_TYPE = "hollywood2-gin-host-metadata-live-probe-v1"
LIVE_STATUS = "observed_public_gin_host_and_registry_metadata"
EVIDENCE_RECORD_TYPE = "hollywood2-gin-host-metadata-evidence-v1"
EVIDENCE_STATUS = "bounded-host-registry-resolution-exact-terms-unresolved"
GIN_COMMIT_SHA1 = "870fa6d6209c9085260918d61433a0a2c70fd497"

GROUND_TRUTH_EVIDENCE_FINGERPRINT_SHA256 = (
    "d5375b8768984ef76da02597c55b225aaff4088fd24698c0d53363e2df6b20ea"
)
ANNOTATION_PROVENANCE_EVIDENCE_FINGERPRINT_SHA256 = (
    "a08510e43caca2a8e6d5c85e7b1ad41c9f312247cd9bd8367372f8ecad8aacab"
)
GIN_HISTORY_EVIDENCE_FINGERPRINT_SHA256 = (
    "c7d2f477a66feca3676482ffdabff2b0778196db99e48b86104fe86d0f5bfae1"
)
UNDERLYING_RIGHTS_EVIDENCE_FINGERPRINT_SHA256 = (
    "6227045c3cc831b3669b34ca74b955847df4b26fafbf825c9a1b5473e25bc943"
)
AUTHOR_LICENSE_EVIDENCE_FINGERPRINT_SHA256 = (
    "b01da719afe18f4eb0103a17d6e8c85f3750ba299050f8026063a9ebb55b1b2e"
)

REVIEWED_GIN_DENIAL_SHA256 = (
    "0d3e98ca727fc1201b436170af5a63f23348aaf146a3ac6234f6c4da283e8b34"
)
REVIEWED_DATACITE = (
    (
        27,
        27,
        "43a965da66f4b7587727e358a3b6780a84f7144fe808f78d837b7786af2f63d5",
    ),
    (
        0,
        0,
        "73cad5cc7fa1c12012f82d1963153aa0e7077956287fa8ecd7b92c333ef7a80f",
    ),
    (
        1,
        1,
        "2e54db785c35e1694f5b45c52febe0d3bc43caf730c3cada46f52b1007797d9e",
    ),
    (
        0,
        0,
        "61a33d8d1b5a659c63bc60cb27fd80af75173a1b2aa0db1b4e35c6533a0fbca1",
    ),
)
EXPECTED_LIVE_PROBE_FINGERPRINT_SHA256 = (
    "42bfa075fb9d577d1e3c4557506f61f0be9ef2a6a25a2ce6c56ff6198c2ef59e"
)
EXPECTED_EVIDENCE_FINGERPRINT_SHA256 = (
    "949ba38f924124f95303c49aaa0478cc2f0a3ee1e412a71fddf8e7d16ee91764"
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _without_fingerprint(record: Mapping[str, Any], key: str) -> dict[str, Any]:
    body = dict(record)
    body.pop(key, None)
    return body


def probe_fingerprint(record: Mapping[str, Any]) -> str:
    """Recompute one live host/registry probe fingerprint."""
    return sha256_bytes(canonical_bytes(_without_fingerprint(record, "probe_fingerprint_sha256")))


def evidence_fingerprint(record: Mapping[str, Any]) -> str:
    """Recompute one frozen host/registry evidence fingerprint."""
    body = _without_fingerprint(record, "evidence_fingerprint_sha256")
    return sha256_bytes(canonical_bytes(body))


def _license_key_paths(value: Any, prefix: str = "") -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if "license" in str(key).lower() or "licence" in str(key).lower():
                if isinstance(child, (str, int, float, bool)) or child is None:
                    safe_value: Any = child
                elif isinstance(child, dict):
                    safe_value = {
                        str(k): v
                        for k, v in child.items()
                        if isinstance(v, (str, int, float, bool)) or v is None
                    }
                else:
                    safe_value = f"<{type(child).__name__}>"
                found.append({"path": path, "value": safe_value})
            found.extend(_license_key_paths(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_license_key_paths(child, f"{prefix}[{index}]"))
    return found


def _contains_repository_url(value: Any) -> bool:
    if isinstance(value, str):
        lower = value.lower().rstrip("/")
        return any(marker.lower().rstrip("/") in lower for marker in REPOSITORY_URL_MARKERS)
    if isinstance(value, dict):
        return any(_contains_repository_url(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_repository_url(child) for child in value)
    return False


def summarize_api(fetch: dict[str, Any]) -> dict[str, Any]:
    """Retain public response identity plus selected repository/license metadata only."""
    summary = {key: value for key, value in fetch.items() if key != "body"}
    body = fetch["body"]
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        summary["json_object"] = False
        summary["license_key_paths"] = []
        return summary

    summary["json_object"] = isinstance(payload, dict)
    if isinstance(payload, dict):
        for key in (
            "id",
            "name",
            "full_name",
            "description",
            "private",
            "archived",
            "empty",
            "default_branch",
            "updated_at",
            "size",
            "website",
        ):
            value = payload.get(key)
            if isinstance(value, (str, int, float, bool)) or value is None:
                summary[key] = value
    summary["license_key_paths"] = _license_key_paths(payload)
    return summary


def summarize_page(fetch: dict[str, Any]) -> dict[str, Any]:
    """Fingerprint the public page and record non-promotional keyword observations."""
    summary = {key: value for key, value in fetch.items() if key != "body"}
    try:
        text = fetch["body"].decode("utf-8").lower()
    except UnicodeDecodeError:
        text = ""
    summary["contains_license_word"] = "license" in text
    summary["contains_licence_word"] = "licence" in text
    summary["contains_repository_slug"] = "hollywood2_em" in text
    return summary


def summarize_datacite(fetch: dict[str, Any]) -> dict[str, Any]:
    """Summarize one bounded DataCite query without retaining unrelated result records."""
    summary = {key: value for key, value in fetch.items() if key != "body"}
    try:
        payload = json.loads(fetch["body"].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        summary.update(
            {
                "json_object": False,
                "reported_total": None,
                "returned_record_count": 0,
                "exact_repository_match_count": 0,
                "exact_repository_matches": [],
            }
        )
        return summary

    summary["json_object"] = isinstance(payload, dict)
    meta = payload.get("meta", {}) if isinstance(payload, dict) else {}
    data = payload.get("data", []) if isinstance(payload, dict) else []
    summary["reported_total"] = meta.get("total") if isinstance(meta, dict) else None
    summary["returned_record_count"] = len(data) if isinstance(data, list) else 0

    matches: list[dict[str, Any]] = []
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            attributes = item.get("attributes", {})
            if not isinstance(attributes, dict) or not _contains_repository_url(attributes):
                continue
            match: dict[str, Any] = {"id": item.get("id")}
            match_fields = (
                "doi",
                "url",
                "publisher",
                "publicationYear",
                "types",
                "titles",
                "rightsList",
            )
            for key in match_fields:
                value = attributes.get(key)
                if isinstance(value, (str, int, float, bool, list, dict)) or value is None:
                    match[key] = value
            matches.append(match)

    summary["exact_repository_match_count"] = len(matches)
    summary["exact_repository_matches"] = matches
    return summary


def _nonempty_license_value(license_paths: list[dict[str, Any]]) -> bool:
    for item in license_paths:
        value = item["value"]
        if isinstance(value, str) and value.strip():
            return True
        if isinstance(value, dict) and any(
            isinstance(v, str) and v.strip() for v in value.values()
        ):
            return True
    return False


def build_probe_record(
    api_fetch: dict[str, Any],
    page_fetch: dict[str, Any],
    datacite_fetches: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build host/registry evidence without converting metadata into permission claims."""
    api = summarize_api(api_fetch)
    page = summarize_page(page_fetch)
    datacite = [summarize_datacite(fetch) for fetch in (datacite_fetches or [])]
    license_paths = api["license_key_paths"]
    datacite_exact_matches = sum(item["exact_repository_match_count"] for item in datacite)

    record: dict[str, Any] = {
        "record_type": LIVE_RECORD_TYPE,
        "status": LIVE_STATUS,
        "repository": REPOSITORY_SLUG,
        "api": api,
        "page": page,
        "datacite_queries": datacite,
        "rights_interpretation": {
            "host_api_metadata_accessible": api.get("http_status") == 200 and api["json_object"],
            "host_api_exposes_license_key": bool(license_paths),
            "host_api_exposes_nonempty_license_value": _nonempty_license_value(license_paths),
            "datacite_exact_repository_match_count": datacite_exact_matches,
            "exact_license_identifier_verified": False,
            "analysis_use_authorized": False,
            "raw_data_redistribution_authorized": False,
            "license_inference_from_page_keyword_permitted": False,
            "registry_zero_match_is_global_absence_claim": False,
        },
        "scientific_boundary": {
            "participant_identity_mapping_verified": False,
            "source_audit_ready": False,
            "participant_disjoint_model_validation_created": False,
            "cross_dataset_validation_created": False,
            "frozen_evidence_performance_claim_created": False,
        },
    }
    record["probe_fingerprint_sha256"] = probe_fingerprint(record)
    return record


def _load_json_object(record_or_path: Mapping[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(record_or_path, Mapping):
        return dict(record_or_path)
    path = Path(record_or_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        message = f"Could not load Hollywood2 GIN host-metadata evidence: {exc}"
        raise BenchmarkIntegrityError(message) from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(
            "Hollywood2 GIN host-metadata evidence must be a JSON object."
        )
    return payload


def _mapping(record: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = record.get(key)
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(f"Hollywood2 GIN host-metadata field {key!r} is missing.")
    return value


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BenchmarkIntegrityError(f"Hollywood2 GIN host-metadata {label} drifted.")


def _true(value: Any, label: str) -> None:
    if value is not True:
        raise BenchmarkIntegrityError(f"Hollywood2 GIN host-metadata must preserve {label}.")


def _false(value: Any, label: str) -> None:
    if value is not False:
        raise BenchmarkIntegrityError(f"Hollywood2 GIN host-metadata must not promote {label}.")


def _validate_frozen_binding(binding: Mapping[str, Any]) -> None:
    _equal(binding.get("repository"), REPO_GIT, "canonical repository")
    _equal(binding.get("commit_sha1"), GIN_COMMIT_SHA1, "canonical GIN commit")
    expected = {
        "authoritative_ground_truth_evidence_fingerprint_sha256": (
            GROUND_TRUTH_EVIDENCE_FINGERPRINT_SHA256
        ),
        "annotation_provenance_evidence_fingerprint_sha256": (
            ANNOTATION_PROVENANCE_EVIDENCE_FINGERPRINT_SHA256
        ),
        "gin_history_evidence_fingerprint_sha256": GIN_HISTORY_EVIDENCE_FINGERPRINT_SHA256,
        "underlying_source_rights_evidence_fingerprint_sha256": (
            UNDERLYING_RIGHTS_EVIDENCE_FINGERPRINT_SHA256
        ),
        "author_license_statement_evidence_fingerprint_sha256": (
            AUTHOR_LICENSE_EVIDENCE_FINGERPRINT_SHA256
        ),
    }
    for key, value in expected.items():
        _equal(binding.get(key), value, key)


def _validate_frozen_observation(observation: Mapping[str, Any]) -> None:
    page = _mapping(observation, "gin_page")
    api = _mapping(observation, "gin_api")
    for surface, label in ((page, "GIN page"), (api, "GIN API")):
        _equal(surface.get("http_status"), 403, f"{label} HTTP status")
        _equal(surface.get("bytes"), 93, f"{label} byte count")
        _equal(surface.get("sha256"), REVIEWED_GIN_DENIAL_SHA256, f"{label} response SHA-256")
        _false(surface.get("metadata_accessible"), f"{label} metadata accessibility")
    _false(api.get("json_object"), "GIN API JSON-object observation")
    _equal(api.get("license_key_paths"), [], "GIN API license key paths")
    _true(
        observation.get("page_and_api_response_sha256_identical"),
        "identical GIN page/API response identity",
    )

    queries = observation.get("datacite_queries")
    if not isinstance(queries, list) or len(queries) != 4:
        raise BenchmarkIntegrityError("Hollywood2 GIN host-metadata DataCite query ledger drifted.")
    labels = ("hollywood2", "hollywood2_em", "ioannis.agtzidis", "exact_repository_fragment")
    for query, label, expected in zip(queries, labels, REVIEWED_DATACITE, strict=True):
        if not isinstance(query, Mapping):
            raise BenchmarkIntegrityError("Hollywood2 GIN host-metadata DataCite row is invalid.")
        total, returned, response_sha = expected
        _equal(query.get("query_label"), label, "DataCite query label")
        _equal(query.get("reported_total"), total, f"DataCite {label} reported total")
        _equal(query.get("returned_record_count"), returned, f"DataCite {label} returned count")
        _equal(query.get("exact_repository_match_count"), 0, f"DataCite {label} exact match")
        _equal(query.get("response_sha256"), response_sha, f"DataCite {label} response SHA-256")


def _validate_rights_boundary(rights: Mapping[str, Any]) -> None:
    _false(rights.get("gin_host_license_metadata_inspected"), "GIN host license inspection")
    _false(rights.get("host_metadata_license_absence_verified"), "host license absence")
    _false(
        rights.get("datacite_exact_repository_registration_recovered"),
        "DataCite exact repository registration",
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
    _false(rights.get("raw_data_redistribution_authorized"), "raw-data redistribution")
    _false(rights.get("registry_zero_match_is_global_absence_claim"), "global registry absence")
    _true(
        rights.get("author_or_host_clarification_required_for_exact_terms"),
        "author/host clarification requirement",
    )


def _validate_scientific_boundary(boundary: Mapping[str, Any]) -> None:
    for key, label in (
        ("participant_identity_mapping_verified", "participant identity mapping"),
        ("source_audit_ready", "source-audit readiness"),
        ("participant_disjoint_model_validation_created", "participant-disjoint validation"),
        ("cross_dataset_validation_created", "cross-dataset validation"),
        ("independent_human_human_agreement_created", "independent human-human agreement"),
        ("frozen_evidence_performance_claim_created", "Frozen Evidence performance claim"),
    ):
        _false(boundary.get(key), label)


def validate_hollywood2_gin_host_metadata_evidence(
    record_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Validate the immutable bounded Hollywood2EM host/registry resolution record."""
    record = _load_json_object(record_or_path)
    _equal(record.get("record_type"), EVIDENCE_RECORD_TYPE, "evidence record type")
    _equal(record.get("status"), EVIDENCE_STATUS, "evidence status")
    _equal(record.get("checked_on"), "2026-09-06", "review date")
    _validate_frozen_binding(_mapping(record, "canonical_repository_binding"))
    _validate_frozen_observation(_mapping(record, "live_observation"))
    _validate_rights_boundary(_mapping(record, "rights_interpretation"))
    _validate_scientific_boundary(_mapping(record, "scientific_boundary"))

    execution = _mapping(record, "execution")
    _equal(execution.get("live_probe_record_type"), LIVE_RECORD_TYPE, "live record type")
    _equal(
        execution.get("live_probe_fingerprint_sha256"),
        EXPECTED_LIVE_PROBE_FINGERPRINT_SHA256,
        "reviewed live-probe fingerprint",
    )
    _equal(
        execution.get("live_probe_json_sha256"),
        "941276dae410d43b69874de12c45439318a8313c0b78b81440092087d322d133",
        "reviewed live-probe JSON SHA-256",
    )
    _equal(execution.get("workflow_run_id"), 34057066048, "workflow run ID")
    _equal(
        execution.get("probe_head_sha"),
        "ed22e018efbd44a0f2ce9f2ee08272084ffdedd6",
        "probe head SHA",
    )
    _equal(execution.get("artifact_id"), 9996290245, "artifact ID")
    _equal(
        execution.get("artifact_zip_sha256"),
        "d2f9168e5ef1016a81fa202bf0f8f3079676ee9a6d405247ab46a3a06f3b645c",
        "artifact ZIP SHA-256",
    )

    stored = str(record.get("evidence_fingerprint_sha256", ""))
    if stored != evidence_fingerprint(record):
        raise BenchmarkIntegrityError(
            "Hollywood2 GIN host-metadata evidence self-fingerprint is invalid."
        )
    if stored != EXPECTED_EVIDENCE_FINGERPRINT_SHA256:
        raise BenchmarkIntegrityError(
            "Hollywood2 GIN host-metadata immutable v1 fingerprint drifted."
        )
    return record


def validate_hollywood2_gin_host_metadata_live_probe(
    probe_or_path: Mapping[str, Any] | str | Path,
    evidence_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Bind a fresh host/registry probe to the frozen conservative evidence boundary."""
    validate_hollywood2_gin_host_metadata_evidence(evidence_or_path)
    probe = _load_json_object(probe_or_path)
    _equal(probe.get("record_type"), LIVE_RECORD_TYPE, "live record type")
    _equal(probe.get("status"), LIVE_STATUS, "live status")
    _equal(probe.get("repository"), REPOSITORY_SLUG, "live repository")
    stored = str(probe.get("probe_fingerprint_sha256", ""))
    if stored != probe_fingerprint(probe):
        raise BenchmarkIntegrityError(
            "Hollywood2 GIN host-metadata live-probe fingerprint is invalid."
        )

    api = _mapping(probe, "api")
    page = _mapping(probe, "page")
    _equal(api.get("http_status"), 403, "fresh GIN API HTTP status")
    _false(api.get("json_object"), "fresh GIN API JSON-object observation")
    _equal(api.get("license_key_paths"), [], "fresh GIN API license key paths")
    _equal(page.get("http_status"), 403, "fresh GIN page HTTP status")
    _equal(api.get("sha256"), page.get("sha256"), "fresh GIN page/API response identity")

    queries = probe.get("datacite_queries")
    if not isinstance(queries, list) or len(queries) != 4:
        raise BenchmarkIntegrityError("Hollywood2 GIN host-metadata fresh query ledger drifted.")
    for query in queries:
        if not isinstance(query, Mapping):
            raise BenchmarkIntegrityError(
                "Hollywood2 GIN host-metadata fresh DataCite row invalid."
            )
        _equal(query.get("http_status"), 200, "fresh DataCite HTTP status")
        _true(query.get("json_object"), "fresh DataCite JSON-object response")
        _equal(query.get("exact_repository_match_count"), 0, "fresh DataCite exact match count")

    rights = _mapping(probe, "rights_interpretation")
    _false(rights.get("host_api_metadata_accessible"), "fresh host API accessibility")
    _false(rights.get("host_api_exposes_license_key"), "fresh host API license-key observation")
    _false(
        rights.get("host_api_exposes_nonempty_license_value"),
        "fresh host API non-empty license value",
    )
    _equal(rights.get("datacite_exact_repository_match_count"), 0, "fresh DataCite exact matches")
    _false(rights.get("exact_license_identifier_verified"), "fresh exact license verification")
    _false(rights.get("analysis_use_authorized"), "fresh analysis-use authorization")
    _false(rights.get("raw_data_redistribution_authorized"), "fresh redistribution authorization")
    _false(
        rights.get("license_inference_from_page_keyword_permitted"),
        "fresh page-keyword license inference",
    )
    _false(rights.get("registry_zero_match_is_global_absence_claim"), "fresh global absence claim")

    live_boundary = _mapping(probe, "scientific_boundary")
    for key, label in (
        ("participant_identity_mapping_verified", "fresh participant mapping"),
        ("source_audit_ready", "fresh source-audit readiness"),
        ("participant_disjoint_model_validation_created", "fresh participant validation"),
        ("cross_dataset_validation_created", "fresh cross-dataset validation"),
        ("frozen_evidence_performance_claim_created", "fresh performance Frozen Evidence"),
    ):
        _false(live_boundary.get(key), label)
    return probe
