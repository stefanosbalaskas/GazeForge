"""Probe the current first-party RIT Gaze-in-the-Wild listing conservatively."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

RIT_LAB_URL = "https://www.rit.edu/science/perception-movement-lab"
LISTING_TEXT = "The Gaze-In-Wild Dataset"
EXPECTED_PUBLICATION_TARGET = "https://pubmed.ncbi.nlm.nih.gov/32054884/"
HISTORICAL_HTTPS_URL = "https://www.cis.rit.edu/~rsk3900/gaze-in-wild/"
USER_AGENT = "GazeForge-GIW-current-listing-probe/1.0"


class ProbeError(RuntimeError):
    """Raised when the current first-party listing cannot be reviewed safely."""


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._href: str | None = None
        self._text: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attributes = dict(attrs)
        href = attributes.get("href")
        self._href = href.strip() if isinstance(href, str) and href.strip() else None
        self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._href is None:
            return
        text = " ".join("".join(self._text).split())
        self.links.append((text, self._href))
        self._href = None
        self._text = []


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def probe_fingerprint(payload: dict[str, Any]) -> str:
    """Return the canonical fingerprint of a normalized live listing probe."""
    body = dict(payload)
    body.pop("probe_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _request(url: str, *, timeout: float = 20.0) -> tuple[int | None, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.status), response.read()
    except urllib.error.HTTPError as exc:
        return int(exc.code), exc.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ProbeError(f"Could not retrieve {url}: {exc}") from exc


def _listing_target(html: bytes) -> str:
    try:
        text = html.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProbeError("Current RIT lab page was not UTF-8 HTML.") from exc
    parser = _LinkParser()
    parser.feed(text)
    matches = [href for label, href in parser.links if label == LISTING_TEXT]
    if len(matches) != 1:
        raise ProbeError(
            f"Expected exactly one {LISTING_TEXT!r} link on the current RIT page; "
            f"observed {len(matches)}."
        )
    return urljoin(RIT_LAB_URL, matches[0])


def _target_class(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host == "pubmed.ncbi.nlm.nih.gov" and parsed.path.rstrip("/") == "/32054884":
        return "publication_pubmed"
    if host.endswith("rit.edu"):
        return "first_party_rit_candidate"
    return "unexpected_external_target"


def build_probe() -> dict[str, Any]:
    """Build a normalized live-state record whose changes require reviewed evidence work."""
    listing_status, listing_html = _request(RIT_LAB_URL)
    if listing_status != 200:
        raise ProbeError(f"Current RIT lab page returned HTTP {listing_status}.")
    target = _listing_target(listing_html)
    target_class = _target_class(target)

    historical_status, _ = _request(HISTORICAL_HTTPS_URL)
    payload: dict[str, Any] = {
        "record_type": "gaze-in-wild-current-first-party-listing-probe-v1",
        "current_first_party_page": {
            "url": RIT_LAB_URL,
            "observed_http_status": listing_status,
            "listing_text": LISTING_TEXT,
            "listing_present_exactly_once": True,
            "listing_target": target,
            "listing_target_class": target_class,
            "listing_target_is_expected_publication": target == EXPECTED_PUBLICATION_TARGET,
            "listing_target_is_direct_dataset_archive_verified": False,
            "dataset_file_rights_terms_found_on_listing": False,
        },
        "historical_endpoint_observation": {
            "url": HISTORICAL_HTTPS_URL,
            "observed_http_status": historical_status,
            "retrieval_succeeded": historical_status == 200,
            "observation_is_global_unavailability_proof": False,
            "observation_is_exact_copy_identity_evidence": False,
        },
        "review_trigger": {
            "listing_target_changed_from_expected_publication": (
                target != EXPECTED_PUBLICATION_TARGET
            ),
            "listing_target_is_first_party_rit_candidate": (
                target_class == "first_party_rit_candidate"
            ),
            "historical_endpoint_status_changed_from_reviewed_502": historical_status != 502,
            "requires_human_evidence_review": (
                target != EXPECTED_PUBLICATION_TARGET or historical_status != 502
            ),
            "automatic_source_or_rights_promotion_permitted": False,
        },
        "scientific_boundary": {
            "current_first_party_listing_verified": True,
            "current_exact_authoritative_copy_obtained": False,
            "dataset_file_rights_resolved": False,
            "analysis_use_permitted": False,
            "redistribution_authorized": False,
            "participant_mapping_verified": False,
            "complete_trial_to_task_mapping_verified": False,
            "distributed_file_sampling_cadence_verified": False,
            "independent_labeller_recoverability_verified": False,
            "human_human_agreement_created": False,
            "participant_disjoint_model_validation_created": False,
            "cross_dataset_performance_created": False,
            "gp3_validity_created": False,
            "frozen_evidence_performance_claim_created": False,
        },
        "claim_limit": (
            "This probe records the current first-party RIT listing target and one bounded "
            "historical-endpoint HTTP observation. A listing or endpoint change triggers human "
            "review and never automatically establishes an exact dataset copy, dataset-file "
            "rights, participant/task mappings, labeller recoverability, agreement, model "
            "performance, cross-dataset validity, or Gazepoint GP3 validity."
        ),
    }
    payload["probe_fingerprint_sha256"] = probe_fingerprint(payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build_probe()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "listing_target": payload["current_first_party_page"]["listing_target"],
                "listing_target_class": payload["current_first_party_page"][
                    "listing_target_class"
                ],
                "historical_http_status": payload["historical_endpoint_observation"][
                    "observed_http_status"
                ],
                "requires_human_evidence_review": payload["review_trigger"][
                    "requires_human_evidence_review"
                ],
                "probe_fingerprint_sha256": payload["probe_fingerprint_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
