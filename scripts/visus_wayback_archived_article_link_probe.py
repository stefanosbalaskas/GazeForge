from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

DOI = "10.3390/s21124143"
OUTPUT = Path("visus_wayback_archived_article_link_probe.json")
USER_AGENT = "GazeForge-VISUS-archived-article-links/1"
MAX_BYTES = 5 * 1024 * 1024

CAPTURES = (
    {
        "name": "article_html_2021",
        "timestamp": "20210618035557",
        "original_url": "https://www.mdpi.com/1424-8220/21/12/4143",
    },
    {
        "name": "article_xml_2022",
        "timestamp": "20220620093900",
        "original_url": "https://www.mdpi.com/1424-8220/21/12/4143/xml",
    },
)


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if key.lower() in {"href", "src"} and value:
                self.hrefs.append(value)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _candidate(url: str) -> bool:
    lower = url.lower()
    return any(token in lower for token in ("/s1", "supp", "-s001"))


def _probe(spec: dict[str, str]) -> dict[str, Any]:
    replay_url = (
        f"https://web.archive.org/web/{spec['timestamp']}id_/"
        f"{spec['original_url']}"
    )
    request = urllib.request.Request(replay_url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise RuntimeError(f"Archived article exceeded guardrail: {spec['name']}")
            status = getattr(response, "status", response.getcode())
            final_url = response.geturl()
            headers = {
                key.lower(): value
                for key, value in response.headers.items()
                if key.lower() in {"content-length", "content-type", "etag", "last-modified"}
            }
    except urllib.error.HTTPError as exc:
        return {
            **spec,
            "replay_url": replay_url,
            "http_status": exc.code,
            "final_url": exc.geturl(),
            "response_headers": {},
            "body_bytes": 0,
            "body_sha256": None,
            "doi_marker_present": False,
            "supplement_text_marker_present": False,
            "candidate_links": [],
        }
    except urllib.error.URLError as exc:
        return {
            **spec,
            "replay_url": replay_url,
            "http_status": None,
            "final_url": None,
            "response_headers": {},
            "body_bytes": 0,
            "body_sha256": None,
            "doi_marker_present": False,
            "supplement_text_marker_present": False,
            "candidate_links": [],
            "network_error": type(exc.reason).__name__,
        }

    text = data.decode("utf-8", errors="replace")
    links: set[str] = set()
    parser = _Links()
    parser.feed(text)
    for value in parser.hrefs:
        resolved = urllib.parse.urljoin(spec["original_url"], value)
        if _candidate(resolved):
            links.add(resolved)
    for match in re.findall(r"https?://[^\s\"'<>]+", text):
        value = match.rstrip(".,;)")
        if _candidate(value):
            links.add(value)

    return {
        **spec,
        "replay_url": replay_url,
        "http_status": status,
        "final_url": final_url,
        "response_headers": headers,
        "body_bytes": len(data),
        "body_sha256": hashlib.sha256(data).hexdigest(),
        "doi_marker_present": DOI.lower() in text.lower(),
        "supplement_text_marker_present": "supplement" in text.lower(),
        "candidate_links": sorted(links),
    }


def main() -> None:
    captures = [_probe(spec) for spec in CAPTURES]
    candidates = sorted(
        {
            link
            for capture in captures
            for link in capture.get("candidate_links", [])
        }
    )
    report: dict[str, Any] = {
        "record_type": "visus-wayback-archived-article-link-probe-v1",
        "provider": "Internet Archive Wayback Machine",
        "article_doi": DOI,
        "captures": captures,
        "historical_supplement_links": candidates,
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
