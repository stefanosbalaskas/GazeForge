#!/usr/bin/env python3
"""Probe the institutional Hollywood-2 gaze source and licence without downloading corpus bytes."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

DESCRIPTION_URL = "https://vision.imar.ro/eyetracking/description.php"
LICENSE_URL = "https://vision.imar.ro/eyetracking/license.php"
RECORD_TYPE = "hollywood2-underlying-source-live-probe-v1"
USER_AGENT = "GazeForge/0.1 source-resolution audit (+https://github.com/stefanosbalaskas/GazeForge)"
_ALLOWED_DOWNLOAD_HOSTS = {"vision.imar.ro", "www.vision.imar.ro"}


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self.links: list[dict[str, str]] = []
        self._href: str | None = None
        self._anchor_text: list[str] = []
        self._suppressed_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript"}:
            self._suppressed_depth += 1
            return
        if self._suppressed_depth:
            return
        if lowered == "a":
            self._href = dict(attrs).get("href")
            self._anchor_text = []

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript"} and self._suppressed_depth:
            self._suppressed_depth -= 1
            return
        if self._suppressed_depth:
            return
        if lowered == "a" and self._href is not None:
            text = _normalise_text(" ".join(self._anchor_text))
            self.links.append({"text": text, "href": self._href})
            self._href = None
            self._anchor_text = []

    def handle_data(self, data: str) -> None:
        if self._suppressed_depth:
            return
        self.text_parts.append(data)
        if self._href is not None:
            self._anchor_text.append(data)


def _normalise_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_fingerprint(payload: dict[str, Any]) -> str:
    body = {key: value for key, value in payload.items() if key != "probe_fingerprint_sha256"}
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return _sha256(encoded)


def _request(url: str, *, method: str = "GET", headers: dict[str, str] | None = None):
    request_headers = {"User-Agent": USER_AGENT, "Accept": "text/html,*/*;q=0.8"}
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(url, headers=request_headers, method=method)
    return urllib.request.urlopen(request, timeout=60)  # noqa: S310 - fixed audited HTTPS origins.


def _fetch_page(url: str) -> dict[str, Any]:
    with _request(url) as response:
        data = response.read()
        final_url = response.geturl()
        status = int(getattr(response, "status", 200))
        content_type = response.headers.get("Content-Type")
    parser = _PageParser()
    parser.feed(data.decode("utf-8", errors="replace"))
    text = _normalise_text(" ".join(parser.text_parts))
    links = [
        {
            "text": item["text"],
            "href": urllib.parse.urljoin(final_url, item["href"]),
        }
        for item in parser.links
        if item["href"]
    ]
    return {
        "requested_url": url,
        "final_url": final_url,
        "http_status": status,
        "content_type": content_type,
        "bytes": len(data),
        "sha256": _sha256(data),
        "normalised_text_sha256": _sha256(text.encode("utf-8")),
        "text": text,
        "links": links,
    }


def _contains_all(text: str, phrases: list[str], *, label: str) -> None:
    lowered = text.lower()
    missing = [phrase for phrase in phrases if phrase.lower() not in lowered]
    if missing:
        raise RuntimeError(f"{label} is missing required authoritative text: {missing}")


def _resolve_download_link(description: dict[str, Any]) -> str:
    candidates = [
        item
        for item in description["links"]
        if "hollywood-2 gaze data" in item["text"].lower()
    ]
    if len(candidates) != 1:
        raise RuntimeError(
            "Institutional description page must expose exactly one Hollywood-2 gaze data link."
        )
    url = candidates[0]["href"]
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in _ALLOWED_DOWNLOAD_HOSTS:
        raise RuntimeError(f"Unexpected Hollywood-2 download origin: {url}")
    return url


def _probe_download_endpoint(url: str) -> dict[str, Any]:
    method = "HEAD"
    try:
        response = _request(url, method="HEAD", headers={"Accept": "*/*"})
    except urllib.error.HTTPError as exc:
        if exc.code not in {400, 403, 405, 501}:
            raise
        method = "GET-range"
        response = _request(url, headers={"Accept": "*/*", "Range": "bytes=0-0"})
    with response:
        final_url = response.geturl()
        parsed = urllib.parse.urlparse(final_url)
        if parsed.scheme != "https" or parsed.hostname not in _ALLOWED_DOWNLOAD_HOSTS:
            raise RuntimeError(f"Hollywood-2 download redirected outside audited origin: {final_url}")
        status = int(getattr(response, "status", 200))
        headers = response.headers
        sampled = b"" if method == "HEAD" else response.read(1)
    return {
        "requested_url": url,
        "final_url": final_url,
        "probe_method": method,
        "http_status": status,
        "content_type": headers.get("Content-Type"),
        "content_length": headers.get("Content-Length"),
        "content_range": headers.get("Content-Range"),
        "content_disposition": headers.get("Content-Disposition"),
        "accept_ranges": headers.get("Accept-Ranges"),
        "sampled_bytes": len(sampled),
        "full_corpus_downloaded": False,
    }


def probe() -> dict[str, Any]:
    description = _fetch_page(DESCRIPTION_URL)
    licence = _fetch_page(LICENSE_URL)

    _contains_all(
        description["text"],
        [
            "Hollywood-2",
            "16 human volunteers",
            "12 active subjects",
            "4 free viewing subjects",
            "SMI iView X HiSpeed 1250",
            "500Hz",
            "1280 x 1024 pixels",
            "47.5 x 29.5cm",
            "60cm",
        ],
        label="Hollywood-2 institutional description",
    )
    _contains_all(
        licence["text"],
        [
            "GRANT OF LICENCE FREE OF CHARGE FOR ACADEMIC USE ONLY",
            "limited, non-exclusive, non-assignable and non-transferable license",
            "may not rent, lease, lend, sub-license or transfer the dataset",
            "RESPONSIBLE USE",
            "ACCEPTANCE OF THIS AGREEMENT",
            "Dynamic Eye Movement Datasets and Learnt Saliency Models for Visual Action Recognition",
            "Actions in the Eye: Dynamic Gaze Datasets and Learnt Saliency Models for Visual Recognition",
        ],
        label="Hollywood-2 institutional licence",
    )

    download_url = _resolve_download_link(description)
    download = _probe_download_endpoint(download_url)

    record: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "status": "verified_institutional_underlying_gaze_source_probe",
        "description_page": {
            key: value for key, value in description.items() if key not in {"text", "links"}
        },
        "licence_page": {
            key: value for key, value in licence.items() if key not in {"text", "links"}
        },
        "download_endpoint": download,
        "verified_recording_context": {
            "participant_count": 16,
            "active_participant_count": 12,
            "free_viewing_participant_count": 4,
            "sampling_rate_hz": 500.0,
            "eye_tracker": "SMI iView X HiSpeed 1250",
            "display_resolution_pixels": [1280, 1024],
            "display_size_cm": [47.5, 29.5],
            "viewing_distance_cm": 60.0,
        },
        "verified_underlying_rights": {
            "academic_use_only": True,
            "limited_nonexclusive_nonassignable_nontransferable": True,
            "standard_grant_allows_dataset_transfer": False,
            "citation_of_mathe_sminchisescu_papers_required": True,
            "commercial_or_other_unpermitted_use_requires_prior_permission": True,
        },
        "scientific_boundary": {
            "underlying_hollywood2_gaze_source_identified": True,
            "underlying_hollywood2_current_description_verified": True,
            "underlying_hollywood2_current_licence_verified": True,
            "underlying_hollywood2_download_endpoint_resolved": True,
            "underlying_hollywood2_corpus_bytes_downloaded": False,
            "underlying_hollywood2_archive_manifest_verified": False,
            "gin_annotation_repository_license_verified": False,
            "gin_annotation_repository_redistribution_verified": False,
            "file_subject_token_to_participant_mapping_verified": False,
            "participant_group_membership_by_file_token_verified": False,
            "model_validation_created": False,
            "cross_dataset_validation_created": False,
        },
    }
    record["probe_fingerprint_sha256"] = _canonical_fingerprint(record)
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="hollywood2_underlying_source_live_probe.json")
    args = parser.parse_args()
    record = probe()
    output = Path(args.output)
    output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
