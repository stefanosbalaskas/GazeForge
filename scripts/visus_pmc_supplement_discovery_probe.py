from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

PMCID = "PMC8235043"
PMID = "34208736"
DOI = "10.3390/s21124143"
BUCKET_HTTPS = "https://pmc-oa-opendata.s3.amazonaws.com"
OUTPUT = Path("visus_pmc_supplement_discovery_probe.json")
USER_AGENT = "GazeForge-VISUS-PMC-supplement-discovery/1"
MAX_METADATA_BYTES = 10 * 1024 * 1024
MAX_LIST_BYTES = 20 * 1024 * 1024
MAX_VERSION_PROBE = 20

_DATA_EXTENSIONS = {
    ".7z",
    ".csv",
    ".dat",
    ".gz",
    ".json",
    ".mat",
    ".ods",
    ".rdata",
    ".rds",
    ".sav",
    ".tar",
    ".tsv",
    ".txt",
    ".xls",
    ".xlsx",
    ".xml",
    ".zip",
}
_IMAGE_EXTENSIONS = {".bmp", ".gif", ".jpeg", ".jpg", ".png", ".svg", ".tif", ".tiff", ".webp"}
_SUPPLEMENT_TOKENS = (
    "supp",
    "supplement",
    "supplementary",
    "supplemental",
    "data_sheet",
    "datasheet",
)


def _fetch(url: str, max_bytes: int) -> tuple[bytes, dict[str, str]]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        declared = response.headers.get("Content-Length")
        if declared is not None and int(declared) > max_bytes:
            raise RuntimeError(f"Response too large for discovery probe: {url}")
        data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise RuntimeError(f"Response exceeded discovery limit: {url}")
        headers = {
            key.lower(): value
            for key, value in response.headers.items()
            if key.lower() in {"content-length", "content-type", "etag", "last-modified"}
        }
    return data, headers


def _try_fetch(url: str, max_bytes: int) -> tuple[bytes, dict[str, str]] | None:
    try:
        return _fetch(url, max_bytes)
    except urllib.error.HTTPError as exc:
        if exc.code in {403, 404}:
            return None
        raise


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _flatten_urls(value: Any) -> list[str]:
    urls: list[str] = []
    if isinstance(value, str):
        if value.startswith(("https://", "http://", "s3://")):
            urls.append(value)
    elif isinstance(value, list):
        for item in value:
            urls.extend(_flatten_urls(item))
    elif isinstance(value, dict):
        for item in value.values():
            urls.extend(_flatten_urls(item))
    return urls


def _xml_text(node: ET.Element, name: str) -> str | None:
    child = next((item for item in node if item.tag.rsplit("}", 1)[-1] == name), None)
    return child.text if child is not None else None


def _list_objects(prefix: str) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode({"list-type": "2", "prefix": prefix})
    url = f"{BUCKET_HTTPS}/?{query}"
    data, _ = _fetch(url, MAX_LIST_BYTES)
    root = ET.fromstring(data)
    objects: list[dict[str, Any]] = []
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1] != "Contents":
            continue
        key = _xml_text(node, "Key")
        size_text = _xml_text(node, "Size")
        if key is None or size_text is None:
            raise RuntimeError("Malformed S3 object listing for PMC article prefix.")
        objects.append(
            {
                "key": key,
                "bytes": int(size_text),
                "etag": (_xml_text(node, "ETag") or "").strip('"'),
                "last_modified": _xml_text(node, "LastModified"),
            }
        )
    if not objects:
        raise RuntimeError(f"No NCBI PMC objects found for prefix {prefix!r}.")
    return sorted(objects, key=lambda row: row["key"])


def _candidate_reason(key: str) -> str | None:
    lower = key.lower()
    suffix = Path(urllib.parse.urlparse(lower).path).suffix
    basename = Path(lower).name
    if any(token in basename for token in _SUPPLEMENT_TOKENS):
        return "supplement-name-token"
    if "/media/" in f"/{lower}" and suffix in _DATA_EXTENSIONS:
        return "media-data-extension"
    if "/media/" in f"/{lower}" and suffix and suffix not in _IMAGE_EXTENSIONS:
        return "media-non-image-object"
    return None


def _url_record(url: str) -> dict[str, Any]:
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    key = urllib.parse.unquote(parsed.path.lstrip("/"))
    return {
        "url": url,
        "object_key": key or None,
        "basename": Path(key).name if key else None,
        "extension": Path(key).suffix.lower() if key else "",
        "md5_query": (query.get("md5") or [None])[0],
        "candidate_reason": _candidate_reason(key),
    }


def main() -> None:
    versions: list[dict[str, Any]] = []
    metadata_payloads: dict[int, dict[str, Any]] = {}
    for version in range(1, MAX_VERSION_PROBE + 1):
        url = f"{BUCKET_HTTPS}/metadata/{PMCID}.{version}.json"
        fetched = _try_fetch(url, MAX_METADATA_BYTES)
        if fetched is None:
            continue
        data, headers = fetched
        try:
            payload = json.loads(data)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid PMC metadata JSON for version {version}.") from exc
        if not isinstance(payload, dict):
            raise RuntimeError(f"PMC metadata version {version} is not a JSON object.")
        metadata_payloads[version] = payload
        versions.append(
            {
                "version": version,
                "url": url,
                "bytes": len(data),
                "sha256": _sha256(data),
                "response_headers": headers,
            }
        )

    if not versions:
        raise RuntimeError(f"No public PMC OA metadata version found for {PMCID}.")

    selected_version = max(row["version"] for row in versions)
    selected_metadata = metadata_payloads[selected_version]
    metadata_text = json.dumps(selected_metadata, sort_keys=True)
    identity_markers = {
        "pmcid_present": PMCID in metadata_text,
        "pmid_present": PMID in metadata_text,
        "doi_present": DOI.lower() in metadata_text.lower(),
    }
    if not all(identity_markers.values()):
        raise RuntimeError(f"PMC metadata identity mismatch: {identity_markers}")

    prefix = f"{PMCID}.{selected_version}/"
    objects = _list_objects(prefix)
    for row in objects:
        row["extension"] = Path(row["key"]).suffix.lower()
        row["candidate_reason"] = _candidate_reason(row["key"])

    media_value = selected_metadata.get("media_urls", [])
    media_urls = sorted(
        (_url_record(url) for url in set(_flatten_urls(media_value))),
        key=lambda row: row["url"],
    )
    candidate_objects = [row for row in objects if row["candidate_reason"] is not None]
    candidate_media_urls = [row for row in media_urls if row["candidate_reason"] is not None]

    report: dict[str, Any] = {
        "record_type": "visus-pmc-supplement-discovery-probe-v1",
        "provider": "NCBI PubMed Central Open Access article datasets on AWS",
        "bucket_https": BUCKET_HTTPS,
        "article_identity": {"pmcid": PMCID, "pmid": PMID, "doi": DOI},
        "metadata_versions": versions,
        "selected_version": selected_version,
        "selected_prefix": prefix,
        "metadata_identity_markers": identity_markers,
        "metadata_top_level_keys": sorted(selected_metadata),
        "metadata_license_code": selected_metadata.get("license_code"),
        "metadata_is_pmc_open_access": selected_metadata.get("is_pmc_open_access"),
        "metadata_is_pmc_openaccess": selected_metadata.get("is_pmc_openaccess"),
        "metadata_is_retracted": selected_metadata.get("is_retracted"),
        "media_urls": media_urls,
        "article_objects": objects,
        "supplement_candidates": {
            "article_objects": candidate_objects,
            "media_urls": candidate_media_urls,
        },
        "scientific_boundary": {
            "supplement_bytes_downloaded": False,
            "supplement_contents_inspected": False,
            "visus_full_source_resolved": False,
            "visus_dataset_license_resolved": False,
            "model_human_validation_created": False,
            "human_human_agreement_created": False,
            "frozen_evidence_created": False,
        },
    }
    report["probe_fingerprint_sha256"] = _sha256(_canonical_bytes(report))
    OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
