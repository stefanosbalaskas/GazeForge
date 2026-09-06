"""Conservative helpers for public Hollywood2EM host and registry metadata."""

from __future__ import annotations

import hashlib
import json
from typing import Any

REPO_PAGE = "https://gin.g-node.org/ioannis.agtzidis/hollywood2_em"
REPO_API = "https://gin.g-node.org/api/v1/repos/ioannis.agtzidis/hollywood2_em"
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


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


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
        "record_type": "hollywood2-gin-host-metadata-live-probe-v1",
        "status": "observed_public_gin_host_and_registry_metadata",
        "repository": "ioannis.agtzidis/hollywood2_em",
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
    record["probe_fingerprint_sha256"] = sha256_bytes(canonical_bytes(record))
    return record
