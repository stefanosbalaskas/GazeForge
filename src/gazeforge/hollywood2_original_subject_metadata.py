"""Conservative public-metadata helpers for the original Hollywood-2 gaze distribution."""

from __future__ import annotations

import hashlib
import json
import re
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

DESCRIPTION_URL = "https://vision.imar.ro/eyetracking/description.php"
LICENSE_URL = "https://vision.imar.ro/eyetracking/license.php"
RECORD_TYPE = "hollywood2-original-subject-metadata-live-probe-v1"
STATUS = "observed-public-original-distribution-metadata"


class _HTMLSummaryParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self.links: list[dict[str, str]] = []
        self._href: str | None = None
        self._anchor_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attr_map = {key.lower(): value for key, value in attrs}
        self._href = attr_map.get("href")
        self._anchor_parts = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.text_parts.append(data)
        if self._href is not None and data.strip():
            self._anchor_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._href is None:
            return
        text = _normalise_space(" ".join(self._anchor_parts))
        self.links.append({"href": self._href, "text": text})
        self._href = None
        self._anchor_parts = []


def _normalise_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def probe_fingerprint(record: dict[str, Any]) -> str:
    body = dict(record)
    body.pop("probe_fingerprint_sha256", None)
    return sha256_bytes(canonical_bytes(body))


def _page_summary(fetch: dict[str, Any], *, base_url: str) -> dict[str, Any]:
    summary = {key: value for key, value in fetch.items() if key != "body"}
    body = fetch.get("body", b"")
    if not isinstance(body, bytes):
        body = b""
    try:
        text = body.decode("utf-8", errors="replace")
    except AttributeError:
        text = ""
    parser = _HTMLSummaryParser()
    parser.feed(text)
    normalized = _normalise_space(" ".join(parser.text_parts))
    summary["normalized_text_sha256"] = sha256_bytes(normalized.encode("utf-8"))
    summary["normalized_text_length"] = len(normalized)
    summary["links"] = [
        {
            "text": link["text"],
            "href": link["href"],
            "resolved_url": urljoin(base_url, link["href"]),
        }
        for link in parser.links
    ]
    summary["normalized_text"] = normalized
    return summary


def summarize_description(fetch: dict[str, Any]) -> dict[str, Any]:
    """Summarize public description metadata without treating it as participant mapping."""
    summary = _page_summary(fetch, base_url=DESCRIPTION_URL)
    text = str(summary.pop("normalized_text", ""))
    lower = text.lower()
    links = summary.pop("links", [])
    data_links = [
        link
        for link in links
        if "hollywood-2" in link["text"].lower() and "gaze data" in link["text"].lower()
    ]
    readme_links = [link for link in links if "readme" in link["text"].lower()]
    summary["markers"] = {
        "sixteen_volunteers": "16 human volunteers" in lower,
        "active_and_free_viewing_split": (
            "active group" in lower and "free-viewing group" in lower
        ),
        "twelve_active_subjects": "12 active subjects" in lower,
        "four_free_viewing_subjects": "4 free viewing subjects" in lower,
        "active_action_recognition_task": "action recognition task" in lower,
        "free_viewing_no_specific_task": "not required to solve any specific task" in lower,
        "five_hundred_hz": "500hz" in lower or "500 hz" in lower,
        "hollywood2_data_link_present": bool(data_links),
        "public_readme_link_present": bool(readme_links),
    }
    summary["hollywood2_data_links"] = data_links
    summary["public_readme_links"] = readme_links
    return summary


def summarize_license(fetch: dict[str, Any]) -> dict[str, Any]:
    """Summarize public original-distribution licence wording without accepting it."""
    summary = _page_summary(fetch, base_url=LICENSE_URL)
    text = str(summary.pop("normalized_text", ""))
    lower = text.lower()
    summary.pop("links", None)
    summary["markers"] = {
        "academic_use_only": "academic use only" in lower,
        "limited_nonexclusive_nonassignable_nontransferable": all(
            term in lower
            for term in ("limited", "non-exclusive", "non-assignable", "non-transferable")
        ),
        "request_from_academic_address": "academic address" in lower,
        "no_sublicense_or_transfer": "sub-license" in lower and "transfer" in lower,
        "responsible_use_permission_clause": "seek prior written permission" in lower,
    }
    return summary


def build_probe_record(
    description_fetch: dict[str, Any],
    license_fetch: dict[str, Any],
    *,
    data_link_head: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a public-metadata record that cannot promote participant or rights claims."""
    description = summarize_description(description_fetch)
    license_summary = summarize_license(license_fetch)
    markers = description["markers"]
    data_links = description["hollywood2_data_links"]
    record: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "status": STATUS,
        "description": description,
        "license_page": license_summary,
        "advertised_data_link_head": data_link_head,
        "observed_subject_context": {
            "public_page_states_sixteen_volunteers": markers["sixteen_volunteers"],
            "public_page_states_twelve_active_subjects": markers["twelve_active_subjects"],
            "public_page_states_four_free_viewing_subjects": markers[
                "four_free_viewing_subjects"
            ],
            "public_page_distinguishes_task_groups": markers["active_and_free_viewing_split"],
            "advertised_hollywood2_data_link_count": len(data_links),
        },
        "rights_boundary": {
            "public_license_page_observed": license_summary.get("http_status") == 200,
            "license_acceptance_or_academic_request_performed": False,
            "dataset_archive_download_performed": False,
            "dataset_use_authorized_by_this_probe": False,
            "dataset_redistribution_authorized_by_this_probe": False,
        },
        "mapping_boundary": {
            "original_subject_ids_recovered_from_public_metadata": False,
            "original_subject_group_id_ledger_recovered": False,
            "gin_token_to_original_subject_id_verified": False,
            "gin_token_to_task_group_verified": False,
            "participant_identity_mapping_verified": False,
            "participant_disjoint_model_validation_created": False,
        },
        "scientific_boundary": {
            "source_audit_ready": False,
            "cross_dataset_validation_created": False,
            "new_empirical_performance_claim_created": False,
        },
    }
    record["probe_fingerprint_sha256"] = probe_fingerprint(record)
    return record
