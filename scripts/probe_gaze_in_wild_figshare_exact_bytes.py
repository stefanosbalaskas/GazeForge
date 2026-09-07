#!/usr/bin/env python
"""Verify exact original-publication Gaze-in-the-Wild Figshare file bytes.

The probe streams the frozen ProcessData and LabelData manifests one file at a
time, verifies exact size and MD5, computes SHA-256, inspects the MATLAB
container schema, and deletes the raw file immediately. ProcessData_cleaned is
explicitly excluded because it is not the original-publication data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any

from scipy.io import whosmat

ALLOWED_LABELS = ("ProcessData", "LabelData")
EXCLUDED_LABEL = "ProcessData_cleaned"
USER_AGENT = "GazeForgeExactByteProbe/1.0"
CHUNK_SIZE = 4 * 1024 * 1024


class ExactByteProbeError(RuntimeError):
    pass


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _manifest_items(frozen: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items = frozen.get("items")
    if not isinstance(items, list):
        raise ExactByteProbeError("Frozen Figshare metadata items must be a list.")
    by_label: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            raise ExactByteProbeError("Frozen Figshare item must be an object.")
        label = str(item.get("label"))
        if label in by_label:
            raise ExactByteProbeError(f"Duplicate Figshare label: {label}")
        by_label[label] = item
    missing = set((*ALLOWED_LABELS, EXCLUDED_LABEL)) - set(by_label)
    if missing:
        raise ExactByteProbeError(f"Frozen Figshare metadata is missing: {sorted(missing)}")
    return by_label


def _expected_md5(row: dict[str, Any]) -> str:
    supplied = row.get("supplied_md5")
    computed = row.get("computed_md5")
    if not isinstance(supplied, str) or not isinstance(computed, str):
        raise ExactByteProbeError(f"Missing MD5 metadata for {row.get('name')}")
    if supplied.lower() != computed.lower():
        raise ExactByteProbeError(f"Frozen MD5 disagreement for {row.get('name')}")
    if len(supplied) != 32:
        raise ExactByteProbeError(f"Invalid MD5 length for {row.get('name')}")
    return supplied.lower()


def _download_verified(row: dict[str, Any], destination: Path, retries: int) -> dict[str, Any]:
    name = str(row.get("name"))
    url = row.get("download_url")
    expected_size = row.get("size")
    if not isinstance(url, str) or not url.startswith("https://"):
        raise ExactByteProbeError(f"Invalid HTTPS download URL for {name}")
    if not isinstance(expected_size, int) or expected_size <= 0:
        raise ExactByteProbeError(f"Invalid expected size for {name}")
    if row.get("is_link_only") is not False:
        raise ExactByteProbeError(f"Refusing link-only Figshare entry: {name}")
    expected_md5 = _expected_md5(row)

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        md5 = hashlib.md5(usedforsecurity=False)
        sha256 = hashlib.sha256()
        observed_size = 0
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=180) as response, destination.open("wb") as out:
                while True:
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    observed_size += len(chunk)
                    if observed_size > expected_size:
                        raise ExactByteProbeError(
                            f"Downloaded bytes exceed frozen size for {name}: "
                            f"{observed_size} > {expected_size}"
                        )
                    md5.update(chunk)
                    sha256.update(chunk)
                    out.write(chunk)
            observed_md5 = md5.hexdigest()
            if observed_size != expected_size:
                raise ExactByteProbeError(
                    f"Size mismatch for {name}: {observed_size} != {expected_size}"
                )
            if observed_md5 != expected_md5:
                raise ExactByteProbeError(
                    f"MD5 mismatch for {name}: {observed_md5} != {expected_md5}"
                )
            return {
                "size_bytes": observed_size,
                "md5": observed_md5,
                "sha256": sha256.hexdigest(),
                "attempt": attempt,
            }
        except Exception as exc:  # network failures are retried; integrity failures still fail eventually
            last_error = exc
            destination.unlink(missing_ok=True)
            if attempt == retries:
                break
            time.sleep(min(2**attempt, 10))
    raise ExactByteProbeError(f"Could not verify {name} after {retries} attempts: {last_error}")


def _mat_schema(path: Path) -> dict[str, Any]:
    try:
        variables = [
            {"name": name, "shape": list(shape), "class": class_name}
            for name, shape, class_name in whosmat(path)
        ]
        return {"format": "matlab-level-5-compatible", "variables": variables}
    except (NotImplementedError, ValueError, OSError) as scipy_error:
        try:
            import h5py

            with h5py.File(path, "r") as handle:
                objects = []
                for name in sorted(handle.keys()):
                    obj = handle[name]
                    row: dict[str, Any] = {"name": name, "kind": type(obj).__name__}
                    shape = getattr(obj, "shape", None)
                    dtype = getattr(obj, "dtype", None)
                    if shape is not None:
                        row["shape"] = list(shape)
                    if dtype is not None:
                        row["dtype"] = str(dtype)
                    objects.append(row)
            return {
                "format": "matlab-7.3-hdf5",
                "root_objects": objects,
                "scipy_probe_error": type(scipy_error).__name__,
            }
        except Exception as hdf_error:
            raise ExactByteProbeError(
                f"Could not inspect MATLAB container {path.name}: "
                f"scipy={scipy_error!r}; h5py={hdf_error!r}"
            ) from hdf_error


def _verify_article(
    item: dict[str, Any],
    temp_dir: Path,
    retries: int,
) -> dict[str, Any]:
    label = str(item["label"])
    files = item.get("files")
    if not isinstance(files, list) or not files:
        raise ExactByteProbeError(f"No frozen files for {label}")
    if int(item.get("file_count", -1)) != len(files):
        raise ExactByteProbeError(f"Frozen file_count mismatch for {label}")

    rows: list[dict[str, Any]] = []
    verified_size = 0
    for index, frozen_row in enumerate(files, start=1):
        if not isinstance(frozen_row, dict):
            raise ExactByteProbeError(f"Invalid file row in {label}")
        name = str(frozen_row.get("name"))
        path = temp_dir / f"{label}-{int(frozen_row['id'])}-{name}"
        print(f"[{label} {index}/{len(files)}] verifying {name}", flush=True)
        identity = _download_verified(frozen_row, path, retries)
        try:
            schema = _mat_schema(path)
        finally:
            path.unlink(missing_ok=True)
        verified_size += identity["size_bytes"]
        rows.append(
            {
                "figshare_file_id": int(frozen_row["id"]),
                "name": name,
                "size_bytes": identity["size_bytes"],
                "md5": identity["md5"],
                "sha256": identity["sha256"],
                "download_attempt": identity["attempt"],
                "mat_schema": schema,
                "raw_bytes_retained": False,
            }
        )

    expected_total = int(item.get("total_size_bytes", -1))
    if verified_size != expected_total:
        raise ExactByteProbeError(
            f"Verified article size mismatch for {label}: {verified_size} != {expected_total}"
        )
    return {
        "label": label,
        "article_id": int(item["id"]),
        "doi": item.get("doi"),
        "license": item.get("license"),
        "frozen_manifest_sha256": item.get("manifest_sha256"),
        "file_count": len(rows),
        "total_size_bytes": verified_size,
        "all_frozen_size_md5_checks_passed": True,
        "raw_bytes_retained": False,
        "files": rows,
        "verified_file_identity_manifest_sha256": _canonical_sha(rows),
    }


def build_probe(frozen_path: Path, retries: int) -> dict[str, Any]:
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    items = _manifest_items(frozen)
    excluded = items[EXCLUDED_LABEL]
    if EXCLUDED_LABEL in ALLOWED_LABELS:
        raise ExactByteProbeError("Internal error: cleaned data must never be an allowed source.")

    with tempfile.TemporaryDirectory(prefix="gazeforge-giw-exact-") as directory:
        temp_dir = Path(directory)
        verified = [_verify_article(items[label], temp_dir, retries) for label in ALLOWED_LABELS]
        leftovers = list(temp_dir.iterdir())
        if leftovers:
            raise ExactByteProbeError(f"Raw-byte cleanup failed: {leftovers}")

    report: dict[str, Any] = {
        "record_type": "gaze-in-wild-figshare-exact-bytes-probe-v1",
        "frozen_metadata": {
            "record_type": frozen.get("record_type"),
            "project_id": frozen.get("project_id"),
            "source_probe_fingerprint_sha256": frozen.get("source_probe_fingerprint_sha256"),
        },
        "verified_items": verified,
        "verified_article_labels": list(ALLOWED_LABELS),
        "verified_file_count": sum(row["file_count"] for row in verified),
        "verified_total_size_bytes": sum(row["total_size_bytes"] for row in verified),
        "exact_original_distribution_bytes_verified": True,
        "raw_dataset_bytes_retained": False,
        "excluded_cleaned_deposit": {
            "label": EXCLUDED_LABEL,
            "article_id": int(excluded["id"]),
            "doi": excluded.get("doi"),
            "downloaded": False,
            "reason": "Not original-publication data; excluded by scientific source contract.",
        },
        "scientific_boundary": {
            "universal_tridx_to_task_mapping_verified": False,
            "complete_file_to_task_mapping_verified": False,
            "participant_disjoint_model_validation_created": False,
            "human_human_agreement_created": False,
            "cross_dataset_validation_created": False,
            "gp3_validity_claim_created": False,
            "quarantine_exit_authorized": False,
            "new_empirical_performance_claim_created": False,
        },
    }
    report["probe_fingerprint_sha256"] = _canonical_sha(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--retries", type=int, default=3)
    args = parser.parse_args()
    if args.retries < 1 or args.retries > 5:
        raise SystemExit("--retries must be between 1 and 5")

    report = build_probe(args.frozen, args.retries)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("verified_file_count", report["verified_file_count"])
    print("verified_total_size_bytes", report["verified_total_size_bytes"])
    print("probe_fingerprint_sha256", report["probe_fingerprint_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
