from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ARTICLE_SLUG = "sensors-21-04143"
BASE_URL = (
    "https://mdpi-res.com/d_attachment/sensors/"
    f"{ARTICLE_SLUG}/article_deploy/{ARTICLE_SLUG}-s001"
)
EXTENSIONS = (
    ".zip",
    ".xlsx",
    ".xls",
    ".csv",
    ".tsv",
    ".txt",
    ".json",
    ".xml",
    ".mat",
    ".7z",
    ".rar",
    ".pdf",
)
OUTPUT = Path("visus_mdpi_static_attachment_probe.json")
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/152.0 Safari/537.36 GazeForge/1"
)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _headers(response: Any) -> dict[str, str]:
    return {
        key.lower(): value
        for key, value in response.headers.items()
        if key.lower()
        in {
            "accept-ranges",
            "content-disposition",
            "content-length",
            "content-range",
            "content-type",
            "etag",
            "last-modified",
            "location",
        }
    }


def _head(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return {
                "url": url,
                "method": "HEAD",
                "http_status": getattr(response, "status", response.getcode()),
                "final_url": response.geturl(),
                "response_headers": _headers(response),
                "body_bytes_read": 0,
            }
    except urllib.error.HTTPError as exc:
        return {
            "url": url,
            "method": "HEAD",
            "http_status": exc.code,
            "final_url": exc.geturl(),
            "response_headers": _headers(exc),
            "body_bytes_read": 0,
        }
    except urllib.error.URLError as exc:
        return {
            "url": url,
            "method": "HEAD",
            "http_status": None,
            "final_url": None,
            "response_headers": {},
            "body_bytes_read": 0,
            "network_error": type(exc.reason).__name__,
        }


def main() -> None:
    probes = [_head(f"{BASE_URL}{extension}") for extension in EXTENSIONS]
    resolved = [
        row
        for row in probes
        if row.get("http_status") in {200, 206}
    ]
    report: dict[str, Any] = {
        "record_type": "visus-mdpi-static-attachment-probe-v1",
        "publisher": "MDPI",
        "article_slug": ARTICLE_SLUG,
        "candidate_base_url": BASE_URL,
        "candidate_basis": (
            "historically observed MDPI d_attachment article_deploy supplementary naming convention; "
            "target filename remains candidate-only until a successful publisher response"
        ),
        "extensions_probed": list(EXTENSIONS),
        "probes": probes,
        "resolved_candidates": resolved,
        "scientific_boundary": {
            "candidate_filename_inferred_not_authoritative": True,
            "supplement_binary_resolved": bool(resolved),
            "supplement_bytes_downloaded": False,
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
