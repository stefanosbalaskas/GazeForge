#!/usr/bin/env python3
"""Probe public original Hollywood-2 metadata without downloading the dataset archive."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from gazeforge.hollywood2_original_subject_metadata import (
    DESCRIPTION_URL,
    LICENSE_URL,
    build_probe_record,
    summarize_description,
)

OUTPUT = Path("hollywood2_original_subject_metadata_live_probe.json")
USER_AGENT = "GazeForge-public-metadata-probe/1.0 (+https://github.com/stefanosbalaskas/GazeForge)"


def fetch(url: str, *, method: str = "GET") -> dict[str, Any]:
    request = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = b"" if method == "HEAD" else response.read(2_000_000)
            return {
                "requested_url": url,
                "final_url": response.geturl(),
                "http_status": response.status,
                "content_type": response.headers.get("Content-Type", ""),
                "content_length": response.headers.get("Content-Length"),
                "content_disposition": response.headers.get("Content-Disposition"),
                "body": body,
            }
    except urllib.error.HTTPError as exc:
        body = b"" if method == "HEAD" else exc.read(64_000)
        return {
            "requested_url": url,
            "final_url": exc.geturl(),
            "http_status": exc.code,
            "content_type": exc.headers.get("Content-Type", ""),
            "content_length": exc.headers.get("Content-Length"),
            "content_disposition": exc.headers.get("Content-Disposition"),
            "body": body,
            "error": f"HTTPError: {exc.reason}",
        }
    except urllib.error.URLError as exc:
        return {
            "requested_url": url,
            "final_url": url,
            "http_status": None,
            "content_type": "",
            "content_length": None,
            "content_disposition": None,
            "body": b"",
            "error": f"URLError: {exc.reason}",
        }


def public_fetch(fetch_record: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in fetch_record.items() if key != "body"}


def main() -> None:
    description = fetch(DESCRIPTION_URL)
    license_page = fetch(LICENSE_URL)
    description_summary = summarize_description(description)
    links = description_summary["hollywood2_data_links"]
    head = fetch(links[0]["resolved_url"], method="HEAD") if len(links) == 1 else None
    record = build_probe_record(
        description,
        license_page,
        data_link_head=public_fetch(head) if head is not None else None,
    )
    OUTPUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
