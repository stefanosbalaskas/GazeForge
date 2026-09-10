from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

OUTPUT = Path("visus_wayback_attachment_history_probe.json")
CDX_URL = "https://web.archive.org/cdx/search/cdx"
USER_AGENT = "GazeForge-VISUS-supplement-history/1"
MAX_BYTES = 5 * 1024 * 1024

QUERIES = (
    {
        "name": "publisher_article_namespace",
        "url": "www.mdpi.com/1424-8220/21/12/4143*",
    },
    {
        "name": "publisher_article_namespace_https",
        "url": "https://www.mdpi.com/1424-8220/21/12/4143*",
    },
    {
        "name": "static_attachment_namespace",
        "url": "mdpi-res.com/d_attachment/sensors/sensors-21-04143/*",
    },
    {
        "name": "static_attachment_namespace_https",
        "url": "https://mdpi-res.com/d_attachment/sensors/sensors-21-04143/*",
    },
)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _query(spec: dict[str, str]) -> dict[str, Any]:
    params = {
        "url": spec["url"],
        "output": "json",
        "fl": "timestamp,original,statuscode,mimetype,digest,length",
        "filter": "statuscode:200",
        "collapse": "urlkey",
        "from": "2021",
        "to": "2026",
    }
    url = f"{CDX_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise RuntimeError(f"Wayback CDX response exceeded guardrail: {spec['name']}")
            status = getattr(response, "status", response.getcode())
            headers = {
                key.lower(): value
                for key, value in response.headers.items()
                if key.lower() in {"content-length", "content-type", "etag", "last-modified"}
            }
    except urllib.error.HTTPError as exc:
        return {
            "name": spec["name"],
            "query_url_pattern": spec["url"],
            "request_url": url,
            "http_status": exc.code,
            "response_headers": {
                key.lower(): value
                for key, value in exc.headers.items()
                if key.lower() in {"content-length", "content-type", "etag", "last-modified"}
            },
            "captures": [],
            "body_sha256": None,
        }
    except urllib.error.URLError as exc:
        return {
            "name": spec["name"],
            "query_url_pattern": spec["url"],
            "request_url": url,
            "http_status": None,
            "response_headers": {},
            "captures": [],
            "body_sha256": None,
            "network_error": type(exc.reason).__name__,
        }

    try:
        payload = json.loads(data)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Wayback CDX returned non-JSON for {spec['name']}.") from exc

    captures: list[dict[str, Any]] = []
    if payload:
        if not isinstance(payload, list) or not isinstance(payload[0], list):
            raise RuntimeError(f"Unexpected Wayback CDX shape for {spec['name']}.")
        header = payload[0]
        for row in payload[1:]:
            if not isinstance(row, list) or len(row) != len(header):
                raise RuntimeError(f"Malformed Wayback CDX row for {spec['name']}.")
            item = dict(zip(header, row))
            original = str(item.get("original", ""))
            lower = original.lower()
            item["supplement_candidate"] = any(
                token in lower
                for token in ("/s1", "supp", "-s001", "attachment", "article_deploy")
            )
            captures.append(item)

    return {
        "name": spec["name"],
        "query_url_pattern": spec["url"],
        "request_url": url,
        "http_status": status,
        "response_headers": headers,
        "captures": captures,
        "body_sha256": hashlib.sha256(data).hexdigest(),
    }


def main() -> None:
    queries = [_query(spec) for spec in QUERIES]
    candidates = sorted(
        {
            str(capture["original"])
            for query in queries
            for capture in query.get("captures", [])
            if capture.get("supplement_candidate") is True
        }
    )
    report: dict[str, Any] = {
        "record_type": "visus-wayback-attachment-history-probe-v1",
        "provider": "Internet Archive Wayback Machine CDX",
        "queries": queries,
        "historical_supplement_candidates": candidates,
        "scientific_boundary": {
            "archive_used_as_link-recovery-lead_only": True,
            "historical_supplement_link_resolved": bool(candidates),
            "archived_supplement_bytes_downloaded": False,
            "supplement_contents_inspected": False,
            "visus_full_source_resolved": False,
            "visus_dataset_license_resolved": False,
            "model_human_validation_created": False,
            "frozen_evidence_created": False,
        },
    }
    report["probe_fingerprint_sha256"] = hashlib.sha256(_canonical_bytes(report)).hexdigest()
    OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
