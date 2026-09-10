from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

DOI = "10.3390/s21124143"
ARTICLE_URL = "https://www.mdpi.com/1424-8220/21/12/4143"
CANDIDATE_URLS = (
    ARTICLE_URL,
    "https://www.mdpi.com/article/10.3390/s21124143/s1",
    "https://www.mdpi.com/1424-8220/21/12/4143/s1",
)
OUTPUT = Path("visus_mdpi_supplement_link_probe.json")
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/152.0 Safari/537.36 GazeForge/1"
)
MAX_TEXT_BYTES = 4 * 1024 * 1024


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.hrefs.append(value)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _candidate_link(url: str) -> bool:
    lower = url.lower()
    return any(
        token in lower
        for token in (
            "/s1",
            "supp",
            "s001",
            "attachment",
            "d_attachment",
            "mdpi-res.com",
            "figshare",
            "sensors-21-04143",
        )
    )


def _headers(response: Any) -> dict[str, str]:
    return {
        key.lower(): value
        for key, value in response.headers.items()
        if key.lower()
        in {
            "content-disposition",
            "content-length",
            "content-type",
            "etag",
            "last-modified",
            "location",
        }
    }


def _is_textual(content_type: str) -> bool:
    lower = content_type.lower()
    return lower.startswith("text/") or "html" in lower or "xml" in lower or "json" in lower


def _probe(url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5",
        },
    )
    try:
        response = urllib.request.urlopen(request, timeout=60)
    except urllib.error.HTTPError as exc:
        return {
            "requested_url": url,
            "http_status": exc.code,
            "final_url": exc.geturl(),
            "response_headers": _headers(exc),
            "body_bytes_read": 0,
            "body_sha256": None,
            "candidate_links": [],
            "binary_response_not_read": False,
        }

    with response:
        status = getattr(response, "status", response.getcode())
        final_url = response.geturl()
        headers = _headers(response)
        content_type = headers.get("content-type", "")
        record: dict[str, Any] = {
            "requested_url": url,
            "http_status": status,
            "final_url": final_url,
            "response_headers": headers,
            "body_bytes_read": 0,
            "body_sha256": None,
            "candidate_links": [],
            "binary_response_not_read": False,
        }
        if not _is_textual(content_type):
            record["binary_response_not_read"] = True
            return record

        data = response.read(MAX_TEXT_BYTES + 1)
        if len(data) > MAX_TEXT_BYTES:
            raise RuntimeError(f"MDPI text response exceeded guardrail: {url}")
        record["body_bytes_read"] = len(data)
        record["body_sha256"] = hashlib.sha256(data).hexdigest()
        text = data.decode("utf-8", errors="replace")
        parser = _Links()
        parser.feed(text)
        links = {
            urllib.parse.urljoin(final_url, href)
            for href in parser.hrefs
            if _candidate_link(urllib.parse.urljoin(final_url, href))
        }
        record["candidate_links"] = sorted(links)
        record["doi_marker_present"] = DOI.lower() in text.lower()
        record["supplement_text_marker_present"] = "supplement" in text.lower()
        return record


def main() -> None:
    probes = [_probe(url) for url in CANDIDATE_URLS]
    discovered_links = sorted(
        {
            link
            for probe in probes
            for link in probe.get("candidate_links", [])
        }
    )
    binary_targets = sorted(
        {
            str(probe["final_url"])
            for probe in probes
            if probe.get("binary_response_not_read") is True
            and int(probe.get("http_status", 0)) == 200
        }
    )
    report: dict[str, Any] = {
        "record_type": "visus-mdpi-supplement-link-probe-v1",
        "publisher": "MDPI",
        "article_doi": DOI,
        "article_url": ARTICLE_URL,
        "probes": probes,
        "discovered_candidate_links": discovered_links,
        "resolved_binary_targets_not_downloaded": binary_targets,
        "scientific_boundary": {
            "supplement_binary_resolved": bool(binary_targets),
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
