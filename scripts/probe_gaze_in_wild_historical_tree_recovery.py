"""Audit every reachable first-author GIW Git tree for data-distribution remnants."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

CANONICAL_REPOSITORY = "https://github.com/RSKothari/Gaze-in-Wild"
PINNED_COMMIT = "52262d44e366a53369e10ca73c5f41daf0e8f1e5"
EXPECTED_COMMIT_COUNT = 56
EXPECTED_ROOT_COMMIT = "054c99d3b88f0ad46cbd0b7d66f4fc38718046f5"
RIT_PROJECT_URL = "http://www.cis.rit.edu/~rsk3900/gaze-in-wild/"

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
    pass


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
        for line in _git(root, "log", "--reverse", "--format=%H", "--", "README.md").splitlines()
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


def build_probe(root: Path, releases_json: Path) -> dict[str, Any]:
    root = root.resolve()
    head = _git(root, "rev-parse", "HEAD")
    if head != PINNED_COMMIT:
        raise ProbeError(f"Expected HEAD {PINNED_COMMIT}, observed {head}.")
    origin = _normalise_origin(_git(root, "remote", "get-url", "origin"))
    if origin != CANONICAL_REPOSITORY:
        raise ProbeError(f"Unexpected origin {origin!r}.")

    commits = [line for line in _git(root, "rev-list", "--reverse", "HEAD").splitlines() if line]
    if len(commits) != EXPECTED_COMMIT_COUNT:
        raise ProbeError(f"Expected {EXPECTED_COMMIT_COUNT} reachable commits, observed {len(commits)}.")
    if commits[0] != EXPECTED_ROOT_COMMIT or commits[-1] != PINNED_COMMIT:
        raise ProbeError("Root/head identity drifted.")

    refs = [line for line in _git(root, "show-ref").splitlines() if line]
    local_branch_refs = sorted(
        line for line in refs if " refs/heads/" in line
    )
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
            "no_reachable_historical_tree_is_authoritative_dataset_copy_proven": True,
            "unreachable_or_external_objects_excluded_from_claim": True,
            "authoritative_original_or_canonical_dataset_copy_obtained": False,
            "original_distribution_equivalence_verified": False,
            "dataset_file_rights_resolved": False,
            "analysis_use_permitted": False,
            "redistribution_authorized": False,
            "quarantine_exit_authorized": False,
            "source_audit_ready": False,
            "empirical_evidence_eligible": False,
        },
        "claim_limit": (
            "This probe audits every Git tree reachable from the pinned first-author "
            "repository HEAD plus visible local branch/tag refs and GitHub releases. "
            "It cannot rule out deleted/unreachable Git objects, historical web-hosted "
            "files, private storage, author-held copies, or other external archives, and "
            "it creates no dataset-file rights or empirical authorization."
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
    print(
        json.dumps(
            {
                "reachable_commit_count": record["reachable_commit_count"],
                "unique_mat_path_count": len(audit["unique_mat_paths"]),
                "unique_exact_giw_data_path_count": len(audit["unique_exact_giw_data_paths"]),
                "unique_alternate_labeller_path_count": len(audit["unique_alternate_labeller_paths"]),
                "unique_process_or_label_named_path_count": len(audit["unique_process_or_label_named_paths"]),
                "unique_archive_path_count": len(audit["unique_archive_paths"]),
                "release_count": record["refs"]["release_count"],
                "probe_fingerprint_sha256": record["probe_fingerprint_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
