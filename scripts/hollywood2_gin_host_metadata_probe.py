"""Probe public GIN host metadata for Hollywood2EM without inferring license terms."""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

OUTPUT = Path("hollywood2_gin_host_metadata_live_probe.json")
REPO_PAGE = "https://gin.g-node.org/ioannis.agtzidis/hollywood2_em"
REPO_API = "https://gin.g-node.org/api/v1/repos/ioannis.agtzidis/hollywood2_em"
USER_AGENT = "GazeForge/hollywood2-gin-host-metadata-probe"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _fetch(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
            body = response.read()
            return {
                "requested_url": url,
                "final_url": response.geturl(),
                "http_status": response.status,
                "content_type": response.headers.get_content_type(),
                "bytes": len(body),
                "sha256": _sha256(body),
                "body": body,
            }
    except urllib.error.HTTPError as exc:
        body = exc.read()
        return {
            "requested_url": url,
            "final_url": exc.geturl(),
            "http_status": exc.code,
            "content_type": exc.headers.get_content_type() if exc.headers else None,
            "bytes": len(body),
            "sha256": _sha256(body),
            "body": body,
        }


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


def _summarize_api(fetch: dict[str, Any]) -> dict[str, Any]:
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


def _summarize_page(fetch: dict[str, Any]) -> dict[str, Any]:
    summary = {key: value for key, value in fetch.items() if key != "body"}
    try:
        text = fetch["body"].decode("utf-8").lower()
    except UnicodeDecodeError:
        text = ""
    summary["contains_license_word"] = "license" in text
    summary["contains_licence_word"] = "licence" in text
    summary["contains_repository_slug"] = "hollywood2_em" in text
    return summary


def build_record(api_fetch: dict[str, Any], page_fetch: dict[str, Any]) -> dict[str, Any]:
    """Build a conservative host-metadata observation record."""
    api = _summarize_api(api_fetch)
    page = _summarize_page(page_fetch)
    license_paths = api["license_key_paths"]
    exact_identifier = False
    if license_paths:
        for item in license_paths:
            value = item["value"]
            if isinstance(value, str) and value.strip():
                exact_identifier = True
            elif isinstance(value, dict) and any(
                isinstance(v, str) and v.strip() for v in value.values()
            ):
                exact_identifier = True

    record: dict[str, Any] = {
        "record_type": "hollywood2-gin-host-metadata-live-probe-v1",
        "status": "observed_public_gin_host_metadata",
        "repository": "ioannis.agtzidis/hollywood2_em",
        "api": api,
        "page": page,
        "rights_interpretation": {
            "host_api_exposes_license_key": bool(license_paths),
            "host_api_exposes_nonempty_license_value": exact_identifier,
            "exact_license_identifier_verified": False,
            "analysis_use_authorized": False,
            "raw_data_redistribution_authorized": False,
            "license_inference_from_page_keyword_permitted": False,
        },
        "scientific_boundary": {
            "participant_identity_mapping_verified": False,
            "source_audit_ready": False,
            "participant_disjoint_model_validation_created": False,
            "cross_dataset_validation_created": False,
            "frozen_evidence_performance_claim_created": False,
        },
    }
    record["probe_fingerprint_sha256"] = _sha256(_canonical_bytes(record))
    return record


def main() -> int:
    api_fetch = _fetch(REPO_API)
    page_fetch = _fetch(REPO_PAGE)
    record = build_record(api_fetch, page_fetch)
    OUTPUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
