from __future__ import annotations

import hashlib
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

PMCID = "PMC8235043"
PMID = "34208736"
DOI = "10.3390/s21124143"
VERSION = 1
BUCKET_HTTPS = "https://pmc-oa-opendata.s3.amazonaws.com"
XML_KEY = f"{PMCID}.{VERSION}/{PMCID}.{VERSION}.xml"
XML_URL = f"{BUCKET_HTTPS}/{XML_KEY}"
EXPECTED_XML_BYTES = 243122
EXPECTED_XML_MD5 = "416bbdf812ce0bfcc03ca3a1abcaf6ce"
OUTPUT = Path("visus_pmc_xml_supplement_link_probe.json")
USER_AGENT = "GazeForge-VISUS-PMC-xml-supplement-link/1"
MAX_XML_BYTES = 5 * 1024 * 1024


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _hrefs(element: ET.Element) -> list[str]:
    return sorted(
        {
            value
            for key, value in element.attrib.items()
            if key.rsplit("}", 1)[-1] in {"href", "url"} and value
        }
    )


def _text(element: ET.Element) -> str:
    return " ".join(" ".join(element.itertext()).split())


def _is_relevant_link(value: str) -> bool:
    lower = value.lower()
    return any(
        token in lower
        for token in (
            "supp",
            "s21124143",
            "sensors-21-04143",
            "mdpi.com",
            "mdpi-res.com",
            "doi.org/10.3390/s21124143",
        )
    )


def main() -> None:
    request = urllib.request.Request(XML_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(MAX_XML_BYTES + 1)
        headers = {
            key.lower(): value
            for key, value in response.headers.items()
            if key.lower() in {"content-length", "content-type", "etag", "last-modified"}
        }
    if len(data) > MAX_XML_BYTES:
        raise RuntimeError("PMC XML exceeded the discovery guardrail.")
    if len(data) != EXPECTED_XML_BYTES:
        raise RuntimeError(f"PMC XML byte size drifted: {len(data)}")
    observed_md5 = hashlib.md5(data).hexdigest()
    if observed_md5 != EXPECTED_XML_MD5:
        raise RuntimeError(f"PMC XML MD5 drifted: {observed_md5}")

    root = ET.fromstring(data)
    xml_text = data.decode("utf-8", errors="strict")
    identity = {
        "pmcid_present": PMCID in xml_text,
        "pmid_present": PMID in xml_text,
        "doi_present": DOI.lower() in xml_text.lower(),
    }
    if not all(identity.values()):
        raise RuntimeError(f"PMC XML identity mismatch: {identity}")

    supplementary_elements: list[dict[str, Any]] = []
    relevant_links: set[str] = set()
    data_availability_sections: list[str] = []
    for element in root.iter():
        name = _local_name(element.tag)
        text = _text(element)
        hrefs = _hrefs(element)
        for href in hrefs:
            if _is_relevant_link(href):
                relevant_links.add(href)
        if "supp" in name.lower() or "supplement" in text[:160].lower():
            supplementary_elements.append(
                {
                    "tag": name,
                    "hrefs": hrefs,
                    "text_preview": text[:300],
                }
            )
        if name == "sec":
            title = next(
                (_text(child) for child in element if _local_name(child.tag) == "title"),
                "",
            )
            if "data availability" in title.lower():
                data_availability_sections.append(text[:1000])

    for match in re.findall(r"https?://[^\s\"'<>]+", xml_text):
        value = match.rstrip(".,;)")
        if _is_relevant_link(value):
            relevant_links.add(value)

    report: dict[str, Any] = {
        "record_type": "visus-pmc-xml-supplement-link-probe-v1",
        "article_identity": {"pmcid": PMCID, "pmid": PMID, "doi": DOI},
        "source": {
            "provider": "NCBI PubMed Central Open Access article datasets on AWS",
            "version": VERSION,
            "xml_key": XML_KEY,
            "xml_url": XML_URL,
            "bytes": len(data),
            "md5": observed_md5,
            "sha256": hashlib.sha256(data).hexdigest(),
            "response_headers": headers,
        },
        "identity_markers": identity,
        "supplementary_elements": supplementary_elements,
        "relevant_external_links": sorted(relevant_links),
        "data_availability_sections": data_availability_sections,
        "scientific_boundary": {
            "publisher_supplement_download_resolved": False,
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
