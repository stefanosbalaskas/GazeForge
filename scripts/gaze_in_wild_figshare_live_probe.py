#!/usr/bin/env python
"""Live metadata-only binding for the official Gaze-in-the-Wild Figshare deposits."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Any

API_BASE = "https://api.figshare.com/v2"
PROJECT_ID = 74580
ARTICLE_IDS = {
    "ProcessData": 11673645,
    "LabelData": 11673696,
    "ProcessData_cleaned": 11673717,
}


def _fetch_json(url: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "GazeForgeEvidenceProbe/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def _canonical_sha(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _files(raw: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        {
            "id": item.get("id"),
            "name": item.get("name"),
            "size": item.get("size"),
            "is_link_only": item.get("is_link_only"),
            "download_url": item.get("download_url"),
            "supplied_md5": item.get("supplied_md5"),
            "computed_md5": item.get("computed_md5"),
        }
        for item in raw.get("files", [])
    ]
    rows.sort(key=lambda row: (str(row["name"]), int(row["id"] or 0)))
    return rows


def _item(label: str, article_id: int) -> dict[str, Any]:
    raw = _fetch_json(f"{API_BASE}/articles/{article_id}")
    files = _files(raw)
    return {
        "label": label,
        "id": raw.get("id"),
        "title": raw.get("title"),
        "doi": raw.get("doi"),
        "url": raw.get("url"),
        "url_public_api": raw.get("url_public_api"),
        "defined_type_name": raw.get("defined_type_name"),
        "version": raw.get("version"),
        "published_date": raw.get("published_date"),
        "modified_date": raw.get("modified_date"),
        "description": raw.get("description"),
        "keywords": raw.get("keywords"),
        "references": raw.get("references"),
        "authors": [
            {
                "id": author.get("id"),
                "full_name": author.get("full_name"),
                "orcid_id": author.get("orcid_id"),
            }
            for author in raw.get("authors", [])
        ],
        "license": raw.get("license"),
        "files": files,
        "manifest_sha256": _canonical_sha(files),
        "file_count": len(files),
        "total_size_bytes": sum(int(row["size"] or 0) for row in files),
    }


def _project_articles() -> list[dict[str, Any]]:
    raw = _fetch_json(f"{API_BASE}/projects/{PROJECT_ID}/articles?page_size=100")
    rows = [
        {
            "id": item.get("id"),
            "title": item.get("title"),
            "doi": item.get("doi"),
            "url": item.get("url"),
            "published_date": item.get("published_date"),
        }
        for item in raw
    ]
    rows.sort(key=lambda row: int(row["id"] or 0))
    return rows


def _stable_frozen(frozen: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_id": frozen["project_id"],
        "project_articles": frozen["project_articles"],
        "items": frozen["items"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    frozen = json.loads(args.frozen.read_text(encoding="utf-8"))
    live = {
        "project_id": PROJECT_ID,
        "project_articles": _project_articles(),
        "items": [
            _item(label, article_id)
            for label, article_id in ARTICLE_IDS.items()
        ],
    }
    live["items"].sort(key=lambda item: str(item["label"]))

    frozen_stable = _stable_frozen(frozen)
    frozen_stable["items"] = sorted(
        frozen_stable["items"],
        key=lambda item: str(item["label"]),
    )
    matched = live == frozen_stable
    report = {
        "record_type": "gaze-in-wild-figshare-live-binding-v1",
        "project_id": PROJECT_ID,
        "matched_frozen_metadata": matched,
        "stable_metadata_fingerprint_sha256": _canonical_sha(live),
        "article_ids": [row["id"] for row in live["project_articles"]],
        "items": {
            item["label"]: {
                "doi": item["doi"],
                "file_count": item["file_count"],
                "total_size_bytes": item["total_size_bytes"],
                "manifest_sha256": item["manifest_sha256"],
                "license": item["license"],
            }
            for item in live["items"]
        },
    }
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if not matched:
        raise SystemExit(
            "Live GIW Figshare metadata no longer matches the frozen review."
        )
    print("live metadata binding passed")
    print(
        "stable metadata fingerprint:",
        report["stable_metadata_fingerprint_sha256"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
