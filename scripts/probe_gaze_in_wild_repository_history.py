"""Probe the complete first-author Gaze-in-the-Wild Git history deterministically."""

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
EXPECTED_ROOT_TREE = "c0fa1ae13c101a8d95b09370970a6012ea97a3d9"
PUBLISHED_DISTRIBUTION_URL = "http://www.cis.rit.edu/~rsk3900/gaze-in-wild/"
KEY_PATHS = (
    "README.md",
    "License.md",
    "DataExtraction/GetParticipantInfo.m",
    "DataExtraction/ReadData_function.m",
    "PlotLabels.m",
)
_DATA_FILE_RE = re.compile(r"(?:^|/)(?:PrIdx_\d+_TrIdx_\d+|.*LabelData.*)\.mat$", re.I)


class ProbeError(RuntimeError):
    """Raised when the pinned repository does not match the reviewed probe contract."""


def _git(root: Path, *args: str, text: bool = True) -> str | bytes:
    command = ["git", "-C", str(root), *args]
    result = subprocess.run(command, check=False, capture_output=True)
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise ProbeError(f"git command failed ({' '.join(args)}): {stderr}")
    if not text:
        return result.stdout
    return result.stdout.decode("utf-8", errors="strict").rstrip("\n")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _fingerprint(payload: dict[str, Any]) -> str:
    body = dict(payload)
    body.pop("probe_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _normalise_origin(value: str) -> str:
    origin = value.strip().removesuffix(".git").rstrip("/")
    if origin.startswith("git@github.com:"):
        origin = "https://github.com/" + origin.removeprefix("git@github.com:")
    return origin


def _first_seen_commit(root: Path, path: str) -> str | None:
    value = _git(
        root,
        "log",
        "--diff-filter=A",
        "--format=%H",
        "--reverse",
        "--",
        path,
    )
    lines = [line for line in str(value).splitlines() if line]
    return lines[0] if lines else None


def _path_blob(root: Path, commit: str, path: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", f"{commit}:{path}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _read_blob(root: Path, commit: str, path: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(root), "show", f"{commit}:{path}"],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.decode("utf-8", errors="replace")


def _commit_row(root: Path, commit: str) -> dict[str, Any]:
    fields = _git(
        root,
        "show",
        "-s",
        "--format=%H%x00%T%x00%P%x00%aI%x00%an%x00%s",
        commit,
    ).split("\x00")
    if len(fields) != 6:
        raise ProbeError(f"Unexpected commit metadata field count for {commit}.")
    sha, tree, parents, authored_at, author_name, subject = fields
    return {
        "sha1": sha,
        "tree_sha1": tree,
        "parent_sha1": [value for value in parents.split() if value],
        "authored_at": authored_at,
        "author_name": author_name,
        "subject": subject,
    }


def _readme_history(root: Path) -> list[dict[str, Any]]:
    commits_text = _git(root, "log", "--format=%H", "--reverse", "--", "README.md")
    rows: list[dict[str, Any]] = []
    previous_blob: str | None = None
    for commit in [line for line in commits_text.splitlines() if line]:
        blob = _path_blob(root, commit, "README.md")
        if blob is None or blob == previous_blob:
            continue
        text = _read_blob(root, commit, "README.md") or ""
        rows.append(
            {
                "commit_sha1": commit,
                "blob_sha1": blob,
                "published_distribution_url_present": PUBLISHED_DISTRIBUTION_URL in text,
                "all_data_files_download_webpage_statement_present": (
                    "To download all data files" in text and "project" in text.lower()
                ),
                "raw_data_over_14tb_statement_present": (
                    "raw data is well over 14TB" in text
                ),
                "raw_data_contact_authors_statement_present": (
                    "contact the authors" in text.lower()
                ),
                "mit_phrase_present": "MIT" in text,
                "license_word_present": "license" in text.lower(),
            }
        )
        previous_blob = blob
    return rows


def build_probe(root: Path) -> dict[str, Any]:
    root = root.resolve()
    if not (root / ".git").exists():
        raise ProbeError("Probe root must be a full Git checkout with .git metadata.")

    head = str(_git(root, "rev-parse", "HEAD"))
    if head != PINNED_COMMIT:
        raise ProbeError(f"Expected pinned HEAD {PINNED_COMMIT}, observed {head}.")

    origin = _normalise_origin(str(_git(root, "remote", "get-url", "origin")))
    if origin != CANONICAL_REPOSITORY:
        raise ProbeError(f"Unexpected origin {origin!r}.")

    if str(_git(root, "status", "--porcelain", "--untracked-files=no")):
        raise ProbeError("Pinned checkout has tracked working-tree changes.")

    commits = [line for line in str(_git(root, "rev-list", "--reverse", "HEAD")).splitlines() if line]
    if len(commits) != EXPECTED_COMMIT_COUNT:
        raise ProbeError(
            f"Expected {EXPECTED_COMMIT_COUNT} commits reachable from pinned HEAD; "
            f"observed {len(commits)}."
        )
    if commits[0] != EXPECTED_ROOT_COMMIT or commits[-1] != PINNED_COMMIT:
        raise ProbeError("Root/head commit identity drifted.")

    root_tree = str(_git(root, "rev-parse", "HEAD^{tree}"))
    if root_tree != EXPECTED_ROOT_TREE:
        raise ProbeError(f"Pinned root tree drifted: {root_tree}.")

    commit_ledger = [_commit_row(root, commit) for commit in commits]
    author_names = sorted({str(row["author_name"]) for row in commit_ledger})

    key_paths: dict[str, Any] = {}
    for path in KEY_PATHS:
        blob = _path_blob(root, PINNED_COMMIT, path)
        first_seen = _first_seen_commit(root, path)
        key_paths[path] = {
            "present_at_pinned_head": blob is not None,
            "pinned_blob_sha1": blob,
            "first_seen_commit_sha1": first_seen,
        }

    license_text = _read_blob(root, PINNED_COMMIT, "License.md") or ""
    readme_text = _read_blob(root, PINNED_COMMIT, "README.md") or ""
    paths = [
        line
        for line in str(_git(root, "ls-tree", "-r", "--name-only", "HEAD")).splitlines()
        if line
    ]
    distributed_data_like_paths = sorted(path for path in paths if _DATA_FILE_RE.search(path))

    readme_history = _readme_history(root)
    payload: dict[str, Any] = {
        "record_type": "gaze-in-wild-official-repository-history-probe-v1",
        "repository": CANONICAL_REPOSITORY,
        "pinned_commit_sha1": PINNED_COMMIT,
        "pinned_root_tree_sha1": root_tree,
        "reachable_commit_count": len(commits),
        "root_commit_sha1": commits[0],
        "commit_ledger": commit_ledger,
        "author_names": author_names,
        "key_path_history": key_paths,
        "readme_history": {
            "unique_blob_count": len(readme_history),
            "revisions": readme_history,
            "pinned_distribution_url_present": PUBLISHED_DISTRIBUTION_URL in readme_text,
            "pinned_all_data_files_download_webpage_statement_present": (
                "To download all data files" in readme_text
            ),
            "pinned_raw_data_over_14tb_statement_present": (
                "raw data is well over 14TB" in readme_text
            ),
            "pinned_raw_data_contact_authors_statement_present": (
                "contact the authors" in readme_text.lower()
            ),
        },
        "software_license_history": {
            "license_file_present_at_pinned_head": bool(license_text),
            "license_file_first_seen_commit_sha1": key_paths["License.md"][
                "first_seen_commit_sha1"
            ],
            "license_file_blob_sha1": key_paths["License.md"]["pinned_blob_sha1"],
            "license_file_identifies_mit": license_text.lstrip().startswith("The MIT License"),
            "license_scope_promoted_to_external_dataset_files": False,
        },
        "repository_tree": {
            "tracked_path_count": len(paths),
            "distributed_process_or_label_mat_paths": distributed_data_like_paths,
            "distributed_process_or_label_mat_path_count": len(distributed_data_like_paths),
            "repository_is_exact_compressed_dataset_copy": False,
        },
        "scientific_boundary": {
            "official_first_author_repository_history_verified": True,
            "exact_external_dataset_copy_obtained": False,
            "external_dataset_file_rights_resolved": False,
            "software_mit_is_external_dataset_license": False,
            "published_distribution_url_is_current_direct_copy_verified": False,
            "participant_identity_mapping_from_history_verified": False,
            "complete_trial_to_task_mapping_from_history_verified": False,
            "human_human_agreement_created": False,
            "participant_disjoint_model_validation_created": False,
            "frozen_evidence_performance_claim_created": False,
        },
        "claim_limit": (
            "This probe verifies the complete reachable history of the pinned first-author "
            "processing repository. It does not turn the repository's MIT software licence "
            "into external dataset-file rights, prove that the historical RIT download URL "
            "is a currently retrievable exact data copy, or create participant mapping, "
            "human-agreement, model-performance, cross-dataset, or GP3-validity evidence."
        ),
    }
    payload["probe_fingerprint_sha256"] = _fingerprint(payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = build_probe(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "reachable_commit_count": payload["reachable_commit_count"],
        "readme_unique_blob_count": payload["readme_history"]["unique_blob_count"],
        "probe_fingerprint_sha256": payload["probe_fingerprint_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
