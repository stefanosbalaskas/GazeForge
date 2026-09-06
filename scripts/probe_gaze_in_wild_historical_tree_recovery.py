"""Audit reachable first-author GIW history and the embedded ProcessData sample."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import loadmat, whosmat

CANONICAL_REPOSITORY = "https://github.com/RSKothari/Gaze-in-Wild"
PINNED_COMMIT = "52262d44e366a53369e10ca73c5f41daf0e8f1e5"
EXPECTED_COMMIT_COUNT = 56
EXPECTED_ROOT_COMMIT = "054c99d3b88f0ad46cbd0b7d66f4fc38718046f5"
RIT_PROJECT_URL = "http://www.cis.rit.edu/~rsk3900/gaze-in-wild/"
PREPROCESSING_ARCHIVE = "DataExtraction/all_preprocessing_steps.zip"
EXPECTED_ARCHIVE_BLOB_SHA1 = "284a64bcf52e686a19a09ff65d83f2328251eb71"
EXPECTED_ARCHIVE_SHA256 = "5deef95a4d847b7b21a37c5d746212549b63217bd64159bec72992d82b575956"
EXPECTED_ARCHIVE_SIZE = 72_109_475
EXPECTED_ARCHIVE_ADDED_COMMIT = "b625bd2b38d60c5f20da4704ed41dbe9ef63a78c"
EXPECTED_ARCHIVE_ADDED_SUBJECT = "added isolated preprocessing code"
EMBEDDED_MEMBER = "exports/ProcessData.mat"
EXPECTED_MEMBER_SHA256 = "d633bbf0a3a9224b71e286ada10a63abe7761264eec7e8c25c94fcf0bbbafc63"
EXPECTED_MEMBER_SIZE = 40_528_499
EXPECTED_MEMBER_CRC32 = "167e450c"

_EXACT_DATA_RE = re.compile(
    r"(?:^|/)PrIdx_\d+_TrIdx_\d+(?:_Lbr_\d+)?\.mat$",
    re.IGNORECASE,
)
_LABEL_ALT_RE = re.compile(
    r"(?:^|/)LabellerIdx_\d+_PrIdx_\d+_TrIdx_\d+\.mat$",
    re.IGNORECASE,
)
_DATA_NAME_RE = re.compile(r"(?:ProcessData|LabelData)", re.IGNORECASE)
_ARCHIVE_RE = re.compile(r"\.(?:zip|7z|rar|tgz|tar|tar\.gz)$", re.IGNORECASE)
_URL_RE = re.compile(r"https?://[^\s)\]>]+")


class ProbeError(RuntimeError):
    """Raised when the pinned source does not match the reviewed probe contract."""


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise ProbeError(f"git {' '.join(args)} failed: {stderr}")
    return result.stdout.decode("utf-8", errors="strict").rstrip("\n")


def _normalise_origin(value: str) -> str:
    origin = value.strip().removesuffix(".git").rstrip("/")
    if origin.startswith("git@github.com:"):
        origin = "https://github.com/" + origin.removeprefix("git@github.com:")
    return origin


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _fingerprint(record: dict[str, Any]) -> str:
    body = dict(record)
    body.pop("probe_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_paths(root: Path, commit: str) -> list[str]:
    return [
        line
        for line in _git(root, "ls-tree", "-r", "--name-only", commit).splitlines()
        if line
    ]


def _readme(root: Path, commit: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(root), "show", f"{commit}:README.md"],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.decode("utf-8", errors="replace")


def _blob(root: Path, commit: str, path: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", f"{commit}:{path}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _readme_revisions(root: Path) -> list[dict[str, Any]]:
    commits = [
        line
        for line in _git(
            root,
            "log",
            "--reverse",
            "--format=%H",
            "--",
            "README.md",
        ).splitlines()
        if line
    ]
    rows: list[dict[str, Any]] = []
    previous_blob: str | None = None
    for commit in commits:
        blob = _blob(root, commit, "README.md")
        if blob is None or blob == previous_blob:
            continue
        text = _readme(root, commit) or ""
        urls = sorted(set(_URL_RE.findall(text)))
        rows.append(
            {
                "commit_sha1": commit,
                "blob_sha1": blob,
                "rit_project_url_present": RIT_PROJECT_URL in text,
                "all_data_files_statement_present": "To download all data files" in text,
                "raw_data_contact_statement_present": "contact the authors" in text.lower(),
                "urls": urls,
            }
        )
        previous_blob = blob
    return rows


def _parse_export_info(raw: bytes) -> dict[str, str]:
    reader = csv.reader(io.StringIO(raw.decode("utf-8", errors="strict")))
    rows = list(reader)
    if not rows or rows[0] != ["key", "value"]:
        raise ProbeError("Unexpected bundled export_info.csv header.")
    result: dict[str, str] = {}
    for row in rows[1:]:
        if len(row) != 2:
            raise ProbeError(f"Unexpected bundled export_info.csv row: {row!r}.")
        result[row[0].rstrip(":")] = row[1]
    return result


def _describe_processdata(process: Any) -> tuple[list[str], dict[str, Any], dict[str, Any]]:
    fields = list(getattr(process, "_fieldnames", []) or [])
    described: dict[str, Any] = {}
    for field in fields:
        value = getattr(process, field)
        row: dict[str, Any] = {"python_type": type(value).__name__}
        if isinstance(value, np.ndarray):
            row["shape"] = list(value.shape)
            row["dtype"] = str(value.dtype)
        elif hasattr(value, "_fieldnames"):
            row["struct_fields"] = list(getattr(value, "_fieldnames", []) or [])
        described[field] = row

    etg = process.ETG
    imu = process.IMU
    zed = process.ZED
    giw = process.GIW
    identity = {
        "PrIdx": int(process.PrIdx),
        "TrIdx": int(process.TrIdx),
        "SR": int(process.SR),
        "DepthPresent": int(process.DepthPresent),
        "timestamp_count": int(np.asarray(process.T).size),
        "ETG.POR_shape": list(np.asarray(etg.POR).shape),
        "ETG.Labels_shape": list(np.asarray(etg.Labels).shape),
        "ETG.Confidence_shape": list(np.asarray(etg.Confidence).shape),
        "IMU.HeadVector_shape": list(np.asarray(imu.HeadVector).shape),
        "ZED.FrameNo_shape": list(np.asarray(zed.FrameNo).shape),
        "GIW.GIWvector_shape": list(np.asarray(giw.GIWvector).shape),
        "Path2Data_sha256": hashlib.sha256(
            str(process.Path2Data).encode("utf-8")
        ).hexdigest(),
    }
    return fields, described, identity


def _archive_audit(root: Path) -> dict[str, Any]:
    archive_path = root / PREPROCESSING_ARCHIVE
    if not archive_path.is_file():
        raise ProbeError(f"Expected preprocessing archive is missing: {PREPROCESSING_ARCHIVE}")

    blob = _blob(root, PINNED_COMMIT, PREPROCESSING_ARCHIVE)
    if blob != EXPECTED_ARCHIVE_BLOB_SHA1:
        raise ProbeError(f"Preprocessing archive blob drifted: {blob!r}.")
    if archive_path.stat().st_size != EXPECTED_ARCHIVE_SIZE:
        raise ProbeError("Preprocessing archive size drifted.")
    archive_sha256 = _sha256(archive_path)
    if archive_sha256 != EXPECTED_ARCHIVE_SHA256:
        raise ProbeError("Preprocessing archive SHA-256 drifted.")

    added_commits = [
        line
        for line in _git(
            root,
            "log",
            "--diff-filter=A",
            "--reverse",
            "--format=%H",
            "--",
            PREPROCESSING_ARCHIVE,
        ).splitlines()
        if line
    ]
    if added_commits != [EXPECTED_ARCHIVE_ADDED_COMMIT]:
        raise ProbeError(f"Unexpected archive-addition history: {added_commits!r}.")
    subject = _git(root, "show", "-s", "--format=%s", EXPECTED_ARCHIVE_ADDED_COMMIT)
    if subject != EXPECTED_ARCHIVE_ADDED_SUBJECT:
        raise ProbeError(f"Unexpected archive addition subject: {subject!r}.")

    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            bad_member = archive.testzip()
            if bad_member is not None:
                raise ProbeError(f"Preprocessing archive CRC failure at {bad_member!r}.")
            infos = [info for info in archive.infolist() if not info.is_dir()]
            members = [
                {
                    "name": info.filename,
                    "file_size": info.file_size,
                    "compress_size": info.compress_size,
                    "crc32": f"{info.CRC:08x}",
                }
                for info in infos
            ]
            names = sorted(info.filename for info in infos)
            mat_members = sorted(name for name in names if name.lower().endswith(".mat"))
            exact_data_members = sorted(name for name in names if _EXACT_DATA_RE.search(name))
            alternate_labeller_members = sorted(
                name for name in names if _LABEL_ALT_RE.search(name)
            )
            labeldata_members = sorted(
                name for name in names if "labeldata" in name.lower()
            )
            nested_archive_members = sorted(name for name in names if _ARCHIVE_RE.search(name))

            member_info = archive.getinfo(EMBEDDED_MEMBER)
            if member_info.file_size != EXPECTED_MEMBER_SIZE:
                raise ProbeError("Embedded ProcessData member size drifted.")
            if f"{member_info.CRC:08x}" != EXPECTED_MEMBER_CRC32:
                raise ProbeError("Embedded ProcessData member CRC drifted.")
            export_info = _parse_export_info(archive.read("exports/export_info.csv"))
            with tempfile.TemporaryDirectory() as tmp:
                target = Path(archive.extract(EMBEDDED_MEMBER, path=tmp))
                member_sha256 = _sha256(target)
                if member_sha256 != EXPECTED_MEMBER_SHA256:
                    raise ProbeError("Embedded ProcessData SHA-256 drifted.")
                variables = [
                    {"name": name, "shape": list(shape), "class": cls}
                    for name, shape, cls in whosmat(target)
                ]
                data = loadmat(
                    target,
                    variable_names=["ProcessData"],
                    squeeze_me=True,
                    struct_as_record=False,
                )
                process = data["ProcessData"]
                fields, field_shapes, identity = _describe_processdata(process)
    except (KeyError, OSError, ValueError, zipfile.BadZipFile) as exc:
        raise ProbeError(f"Could not inspect preprocessing archive: {exc}") from exc

    expected_identity = {
        "PrIdx": 2,
        "TrIdx": 2,
        "SR": 300,
        "DepthPresent": 0,
        "timestamp_count": 106_225,
        "ETG.POR_shape": [106_225, 2],
        "ETG.Labels_shape": [106_225],
        "ETG.Confidence_shape": [106_225],
        "IMU.HeadVector_shape": [106_225, 3],
        "ZED.FrameNo_shape": [106_225],
        "GIW.GIWvector_shape": [106_225, 3],
        "Path2Data_sha256":
            "8058c7143cf9104f3802ee7578792db8c48ad74d2515d27e993c435ed126ff4d",
    }
    if identity != expected_identity:
        raise ProbeError("Embedded ProcessData structural identity drifted.")

    return {
        "path": PREPROCESSING_ARCHIVE,
        "blob_sha1": blob,
        "sha256": archive_sha256,
        "size_bytes": archive_path.stat().st_size,
        "added_commit_sha1": EXPECTED_ARCHIVE_ADDED_COMMIT,
        "added_commit_subject": subject,
        "member_count": len(members),
        "members": members,
        "mat_members": mat_members,
        "exact_giw_data_members": exact_data_members,
        "alternate_labeller_members": alternate_labeller_members,
        "labeldata_members": labeldata_members,
        "nested_archive_members": nested_archive_members,
        "export_info": export_info,
        "embedded_processdata": {
            "member_path": EMBEDDED_MEMBER,
            "member_size_bytes": EXPECTED_MEMBER_SIZE,
            "member_crc32": EXPECTED_MEMBER_CRC32,
            "member_sha256": member_sha256,
            "top_level_variables": variables,
            "processdata_fields": fields,
            "processdata_field_shapes": field_shapes,
            "identity": identity,
            "first_party_data_bearing_processdata_object_verified": True,
            "published_distribution_filename_match": False,
            "exact_distribution_file_equivalence_verified": False,
            "separate_labeldata_recovered": False,
            "independent_labeller_streams_recovered": False,
        },
        "dataset_distribution_archive_proven": False,
    }


def build_probe(root: Path, releases_json: Path) -> dict[str, Any]:
    """Build a deterministic recovery-provenance observation."""
    root = root.resolve()
    head = _git(root, "rev-parse", "HEAD")
    if head != PINNED_COMMIT:
        raise ProbeError(f"Expected HEAD {PINNED_COMMIT}, observed {head}.")
    origin = _normalise_origin(_git(root, "remote", "get-url", "origin"))
    if origin != CANONICAL_REPOSITORY:
        raise ProbeError(f"Unexpected origin {origin!r}.")

    commits = [
        line for line in _git(root, "rev-list", "--reverse", "HEAD").splitlines() if line
    ]
    if len(commits) != EXPECTED_COMMIT_COUNT:
        raise ProbeError(
            f"Expected {EXPECTED_COMMIT_COUNT} reachable commits, observed {len(commits)}."
        )
    if commits[0] != EXPECTED_ROOT_COMMIT or commits[-1] != PINNED_COMMIT:
        raise ProbeError("Root/head identity drifted.")

    refs = [line for line in _git(root, "show-ref").splitlines() if line]
    local_branch_refs = sorted(line for line in refs if " refs/heads/" in line)
    tag_refs = sorted(line for line in refs if " refs/tags/" in line)

    unique_mat_paths: set[str] = set()
    unique_exact_data_paths: set[str] = set()
    unique_alt_label_paths: set[str] = set()
    unique_named_data_paths: set[str] = set()
    unique_archive_paths: set[str] = set()
    commits_with_mat_paths: list[str] = []
    commits_with_distribution_like_paths: list[str] = []
    per_commit: list[dict[str, Any]] = []

    for commit in commits:
        paths = _tree_paths(root, commit)
        mat_paths = sorted(path for path in paths if path.lower().endswith(".mat"))
        exact_data_paths = sorted(path for path in paths if _EXACT_DATA_RE.search(path))
        alt_label_paths = sorted(path for path in paths if _LABEL_ALT_RE.search(path))
        named_data_paths = sorted(path for path in paths if _DATA_NAME_RE.search(path))
        archive_paths = sorted(path for path in paths if _ARCHIVE_RE.search(path))
        distribution_like = sorted(
            set(exact_data_paths + alt_label_paths + named_data_paths + archive_paths)
        )
        if mat_paths:
            commits_with_mat_paths.append(commit)
        if distribution_like:
            commits_with_distribution_like_paths.append(commit)
        unique_mat_paths.update(mat_paths)
        unique_exact_data_paths.update(exact_data_paths)
        unique_alt_label_paths.update(alt_label_paths)
        unique_named_data_paths.update(named_data_paths)
        unique_archive_paths.update(archive_paths)
        per_commit.append(
            {
                "commit_sha1": commit,
                "tracked_path_count": len(paths),
                "mat_path_count": len(mat_paths),
                "distribution_like_path_count": len(distribution_like),
            }
        )

    try:
        releases = json.loads(releases_json.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProbeError(f"Could not load releases JSON: {exc}") from exc
    if not isinstance(releases, list):
        raise ProbeError("GitHub releases response must be a JSON list.")

    readmes = _readme_revisions(root)
    all_readme_urls = sorted({url for row in readmes for url in row["urls"]})
    distribution_url_candidates = sorted(
        url
        for url in all_readme_urls
        if "gaze-in-wild" in url.lower() or "ProcessData" in url or "LabelData" in url
    )
    archive_audit = _archive_audit(root)

    record: dict[str, Any] = {
        "record_type": "gaze-in-wild-historical-tree-recovery-probe-v1",
        "repository": CANONICAL_REPOSITORY,
        "pinned_commit_sha1": PINNED_COMMIT,
        "root_commit_sha1": EXPECTED_ROOT_COMMIT,
        "reachable_commit_count": len(commits),
        "refs": {
            "local_branch_refs": local_branch_refs,
            "tag_refs": tag_refs,
            "release_count": len(releases),
        },
        "historical_tree_audit": {
            "commit_tree_count": len(per_commit),
            "commits": per_commit,
            "commits_with_any_mat_paths": commits_with_mat_paths,
            "commits_with_distribution_like_paths": commits_with_distribution_like_paths,
            "unique_mat_paths": sorted(unique_mat_paths),
            "unique_exact_giw_data_paths": sorted(unique_exact_data_paths),
            "unique_alternate_labeller_paths": sorted(unique_alt_label_paths),
            "unique_process_or_label_named_paths": sorted(unique_named_data_paths),
            "unique_archive_paths": sorted(unique_archive_paths),
        },
        "preprocessing_archive_audit": archive_audit,
        "readme_endpoint_history": {
            "unique_revision_count": len(readmes),
            "revisions": readmes,
            "all_urls": all_readme_urls,
            "distribution_url_candidates": distribution_url_candidates,
            "only_known_distribution_project_page": (
                distribution_url_candidates == [RIT_PROJECT_URL]
            ),
        },
        "scientific_boundary": {
            "all_reachable_commit_trees_checked": True,
            "preprocessing_archive_members_checked": True,
            "embedded_first_party_processdata_object_verified": True,
            "unreachable_or_external_objects_excluded_from_claim": True,
            "full_distribution_recovered": False,
            "authoritative_original_or_canonical_dataset_copy_obtained": False,
            "original_distribution_equivalence_verified": False,
            "dataset_file_rights_resolved": False,
            "analysis_use_permitted": False,
            "redistribution_authorized": False,
            "quarantine_exit_authorized": False,
            "source_audit_ready": False,
            "independent_labeller_recoverability_verified": False,
            "empirical_evidence_eligible": False,
        },
        "claim_limit": (
            "This probe verifies one data-bearing ProcessData object embedded in the pinned "
            "first-author preprocessing-code ZIP and audits all Git trees reachable from the "
            "pinned repository HEAD plus visible local branch/tag refs and GitHub releases. "
            "The embedded object is not promoted to byte equivalence with the historical "
            "PrIdx_2_TrIdx_2.mat distribution file, and its ETG.Labels field is not promoted "
            "to recovery of separate LabelData or independent labeller streams. The probe "
            "cannot rule out deleted/unreachable Git objects, historical web-hosted files, "
            "private storage, author-held copies, or other external archives and creates no "
            "dataset-file rights or empirical authorization."
        ),
    }
    record["probe_fingerprint_sha256"] = _fingerprint(record)
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--releases-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    record = build_probe(args.root, args.releases_json)
    args.output.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    audit = record["historical_tree_audit"]
    archive = record["preprocessing_archive_audit"]
    sample = archive["embedded_processdata"]
    print(
        json.dumps(
            {
                "reachable_commit_count": record["reachable_commit_count"],
                "unique_mat_path_count": len(audit["unique_mat_paths"]),
                "unique_exact_giw_data_path_count": len(
                    audit["unique_exact_giw_data_paths"]
                ),
                "preprocessing_archive_member_count": archive["member_count"],
                "embedded_processdata_sha256": sample["member_sha256"],
                "embedded_PrIdx": sample["identity"]["PrIdx"],
                "embedded_TrIdx": sample["identity"]["TrIdx"],
                "embedded_SR": sample["identity"]["SR"],
                "embedded_timestamp_count": sample["identity"]["timestamp_count"],
                "labeldata_member_count": len(archive["labeldata_members"]),
                "release_count": record["refs"]["release_count"],
                "probe_fingerprint_sha256": record["probe_fingerprint_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
