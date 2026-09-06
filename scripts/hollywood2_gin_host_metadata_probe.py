"""Probe public GIN host metadata for Hollywood2EM without inferring license terms."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from gazeforge.hollywood2_gin_host_metadata import (
    REPO_API,
    REPO_PAGE,
    build_probe_record,
    sha256_bytes,
)

OUTPUT = Path("hollywood2_gin_host_metadata_live_probe.json")
USER_AGENT = "GazeForge/hollywood2-gin-host-metadata-probe"


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
                "sha256": sha256_bytes(body),
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
            "sha256": sha256_bytes(body),
            "body": body,
        }


def main() -> int:
    record = build_probe_record(_fetch(REPO_API), _fetch(REPO_PAGE))
    OUTPUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
