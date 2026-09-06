"""Metadata-only inspection of pinned Hollywood2EM ARFF headers.

This module deliberately stops before every ARFF ``@data`` section.  It can
observe header vocabulary and schema signatures, but it cannot by itself verify
coordinate units, participant identities, rights, or empirical validity.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError

RECORD_TYPE = "hollywood2-coordinate-metadata-live-probe-v1"
STATUS = "observed-pinned-arff-header-metadata"
DEFAULT_REPOSITORY = "https://gin.g-node.org/ioannis.agtzidis/hollywood2_em.git"
DEFAULT_COMMIT_SHA1 = "870fa6d6209c9085260918d61433a0a2c70fd497"
HEADER_BYTE_LIMIT = 262_144

_ATTRIBUTE_RE = re.compile(
    r"^@attribute\s+(?:\"([^\"]+)\"|'([^']+)'|(\S+))\s+(.+)$",
    flags=re.IGNORECASE,
)

_MARKERS = {
    "pixel_or_px": ("pixel", " px", "px ", "_px"),
    "screen": ("screen",),
    "resolution": ("resolution",),
    "width": ("width",),
    "height": ("height",),
    "monitor_or_display": ("monitor", "display"),
    "stimulus_or_video": ("stimulus", "video"),
    "degree_or_visual_angle": ("degree", "visual angle"),
}

_REQUIRED_GAZE_ATTRIBUTES = (
    "time",
    "x",
    "y",
    "confidence",
    "handlabeller_1",
    "handlabeller_final",
)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def probe_fingerprint(record: dict[str, Any]) -> str:
    """Return a deterministic fingerprint excluding the stored fingerprint."""
    body = dict(record)
    body.pop("probe_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _read_header(path: Path) -> tuple[bytes, list[str]]:
    """Read one ARFF header and stop before the first data row."""
    pieces: list[bytes] = []
    total = 0
    found_data = False
    with path.open("rb") as handle:
        while True:
            line = handle.readline()
            if not line:
                break
            total += len(line)
            if total > HEADER_BYTE_LIMIT:
                raise BenchmarkIntegrityError(
                    f"Hollywood2 ARFF header exceeded {HEADER_BYTE_LIMIT} bytes."
                )
            stripped = line.lstrip().lower()
            if stripped.startswith(b"@data"):
                pieces.append(line)
                found_data = True
                break
            pieces.append(line)
    if not found_data:
        raise BenchmarkIntegrityError("Hollywood2 ARFF header is missing an @data marker.")
    header = b"".join(pieces)
    text = header.decode("utf-8", errors="replace")
    return header, text.splitlines()


def inspect_hollywood2_arff_header(path: str | Path) -> dict[str, Any]:
    """Inspect one ARFF header without reading or returning source rows."""
    file_path = Path(path)
    if file_path.suffix.lower() != ".arff":
        raise ValueError("Hollywood2 coordinate metadata inspection requires an .arff file.")
    header, lines = _read_header(file_path)
    attributes: list[str] = []
    attribute_types: list[str] = []
    header_text = "\n".join(lines).lower()
    for line in lines:
        match = _ATTRIBUTE_RE.match(line.strip())
        if match is None:
            continue
        name = next(group for group in match.groups()[:3] if group is not None)
        attributes.append(name.strip().lower())
        attribute_types.append(match.group(4).strip().lower())

    markers = {
        name: any(token in header_text for token in tokens)
        for name, tokens in _MARKERS.items()
    }
    return {
        "header_sha256": hashlib.sha256(header).hexdigest(),
        "header_bytes": len(header),
        "data_marker_found": True,
        "attributes": attributes,
        "attribute_types": attribute_types,
        "required_gaze_attributes_present": all(
            name in attributes for name in _REQUIRED_GAZE_ATTRIBUTES
        ),
        "markers": markers,
        "raw_source_rows_read": False,
        "raw_source_rows_embedded": False,
        "source_filename_embedded": False,
    }


def build_hollywood2_coordinate_metadata_probe(
    source_root: str | Path,
    *,
    repository: str = DEFAULT_REPOSITORY,
    commit_sha1: str = DEFAULT_COMMIT_SHA1,
) -> dict[str, Any]:
    """Aggregate header-only observations across the pinned Hollywood2EM tree."""
    root = Path(source_root)
    data_root = root / "ground_truth" if (root / "ground_truth").is_dir() else root
    paths = sorted(data_root.rglob("*.arff"))
    if not paths:
        raise FileNotFoundError(f"No Hollywood2 ARFF files were found under {data_root}.")

    marker_counts: Counter[str] = Counter()
    signature_counts: Counter[tuple[str, ...]] = Counter()
    required_schema_count = 0
    header_hashes: set[str] = set()
    max_header_bytes = 0

    for path in paths:
        observation = inspect_hollywood2_arff_header(path)
        signature = tuple(observation["attributes"])
        signature_counts[signature] += 1
        if observation["required_gaze_attributes_present"]:
            required_schema_count += 1
        for marker, present in observation["markers"].items():
            if present:
                marker_counts[marker] += 1
        header_hashes.add(str(observation["header_sha256"]))
        max_header_bytes = max(max_header_bytes, int(observation["header_bytes"]))

    signatures = [
        {"attributes": list(signature), "file_count": count}
        for signature, count in sorted(
            signature_counts.items(), key=lambda item: (-item[1], item[0])
        )
    ]
    record: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "status": STATUS,
        "source_binding": {
            "repository": str(repository),
            "commit_sha1": str(commit_sha1),
        },
        "header_inventory": {
            "arff_file_count": len(paths),
            "unique_header_sha256_count": len(header_hashes),
            "max_header_bytes": max_header_bytes,
            "required_gaze_schema_file_count": required_schema_count,
            "attribute_signatures": signatures,
            "marker_file_counts": {
                marker: marker_counts.get(marker, 0) for marker in _MARKERS
            },
        },
        "coordinate_boundary": {
            "header_vocabulary_observed": True,
            "coordinate_unit_candidate": "pixels",
            "coordinate_unit_verified": False,
            "coordinate_verification_basis_created": False,
            "pixel_to_visual_angle_conversion_verified": False,
            "unit_sensitive_cross_dataset_modelling_ready": False,
        },
        "mapping_boundary": {
            "participant_identity_mapping_verified": False,
            "source_token_to_participant_mapping_verified": False,
        },
        "rights_boundary": {
            "new_rights_permission_created": False,
            "raw_source_redistribution_authorized": False,
        },
        "scientific_boundary": {
            "raw_source_rows_read": False,
            "raw_source_rows_embedded": False,
            "source_filenames_embedded": False,
            "participant_disjoint_validation_created": False,
            "cross_dataset_validation_created": False,
            "new_empirical_performance_claim_created": False,
        },
    }
    record["probe_fingerprint_sha256"] = probe_fingerprint(record)
    return record
