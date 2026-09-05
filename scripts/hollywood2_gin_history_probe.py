#!/usr/bin/env python3
"""Audit the complete Git history of the canonical Hollywood2EM GIN repository."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

REPOSITORY = "https://gin.g-node.org/ioannis.agtzidis/hollywood2_em.git"
PINNED_HEAD = "870fa6d6209c9085260918d61433a0a2c70fd497"
RECORD_TYPE = "hollywood2-gin-history-probe-v1"
LICENSE_NAMES = {
    "license",
    "license.md",
    "license.txt",
    "copying",
    "copying.md",
    "copying.txt",
}
README_NAMES = {"readme", "readme.md", "readme.txt", "readme.rst"}
TOKEN_RE = re.compile(r"^(?P<token>\d{3})_(?P<clip>.+)\.arff$", re.IGNORECASE)


def _run(
    *args: str,
    cwd: Path | None = None,
    timeout: int = 600,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("GIT_TERMINAL_PROMPT", "0")
    result = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    if check and result.returncode != 0:
        command = " ".join(args)
        raise RuntimeError(
            f"Command failed ({result.returncode}): {command}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def _canonical_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256(payload: Any) -> str:
    if isinstance(payload, bytes):
        data = payload
    else:
        data = _canonical_bytes(payload)
    return hashlib.sha256(data).hexdigest()


def _fingerprint(record: dict[str, Any]) -> str:
    body = {key: value for key, value in record.items() if key != "probe_fingerprint_sha256"}
    return _sha256(body)


def _commit_rows(repo: Path, ref: str) -> list[dict[str, Any]]:
    fmt = "%H%x1f%P%x1f%aI%x1f%an%x1f%ae%x1f%s"
    text = _run("git", "log", "--reverse", f"--format={fmt}", ref, cwd=repo).stdout
    rows: list[dict[str, Any]] = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        parts = raw.split("\x1f")
        if len(parts) != 6:
            raise RuntimeError(f"Unexpected git-log record: {raw!r}")
        sha, parents, author_date, author_name, author_email, subject = parts
        rows.append(
            {
                "commit_sha1": sha,
                "parents": parents.split() if parents else [],
                "author_date": author_date,
                "author_name": author_name,
                "author_email": author_email,
                "subject": subject,
            }
        )
    return rows


def _paths(repo: Path, commit: str) -> list[str]:
    text = _run("git", "ls-tree", "-r", "--name-only", commit, cwd=repo).stdout
    return sorted(line.strip() for line in text.splitlines() if line.strip())


def _blob_sha(repo: Path, commit: str, path: str) -> str:
    text = _run("git", "rev-parse", f"{commit}:{path}", cwd=repo).stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", text):
        raise RuntimeError(f"Could not resolve blob SHA for {commit}:{path}")
    return text


def _blob_bytes(repo: Path, commit: str, path: str) -> bytes:
    env = os.environ.copy()
    env.setdefault("GIT_TERMINAL_PROMPT", "0")
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=repo,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=300,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Could not read {commit}:{path}: {result.stderr.decode(errors='replace')}"
        )
    return result.stdout


def _readme_record(repo: Path, commit: str, path: str) -> dict[str, Any]:
    data = _blob_bytes(repo, commit, path)
    text = data.decode("utf-8", errors="replace")
    keywords = (
        "license",
        "licence",
        "subject",
        "participant",
        "observer",
        "identity",
        " id ",
    )
    matching_lines = [
        line.strip()
        for line in text.splitlines()
        if any(keyword in f" {line.lower()} " for keyword in keywords)
    ]
    return {
        "path": path,
        "git_blob_sha1": _blob_sha(repo, commit, path),
        "bytes": len(data),
        "sha256": _sha256(data),
        "keyword_lines": matching_lines,
    }


def _ground_truth_summary(paths: list[str]) -> dict[str, Any]:
    gt_paths = [
        path
        for path in paths
        if path.startswith("ground_truth/") and path.lower().endswith(".arff")
    ]
    tokens: set[str] = set()
    clips: set[str] = set()
    malformed: list[str] = []
    for path in gt_paths:
        parts = PurePosixPath(path).parts
        if len(parts) < 4:
            malformed.append(path)
            continue
        filename = parts[-1]
        match = TOKEN_RE.match(filename)
        if match is None:
            malformed.append(path)
            continue
        tokens.add(match.group("token"))
        clips.add(match.group("clip"))
        if match.group("clip") != parts[-2]:
            malformed.append(path)
    return {
        "file_count": len(gt_paths),
        "path_fingerprint_sha256": _sha256(gt_paths),
        "file_subject_tokens": sorted(tokens),
        "file_subject_token_count": len(tokens),
        "clip_ids": sorted(clips),
        "clip_count": len(clips),
        "filename_schema_match": len(malformed) == 0,
        "filename_schema_mismatches": malformed,
    }


def _history(repo: Path, ref: str) -> dict[str, Any]:
    commits = _commit_rows(repo, ref)
    if not commits:
        raise RuntimeError("Canonical Hollywood2EM repository has no commits.")

    license_occurrences: list[dict[str, Any]] = []
    readme_versions: dict[tuple[str, str], dict[str, Any]] = {}
    ground_versions: list[dict[str, Any]] = []
    first_seen: dict[str, str] = {}
    commit_summaries: list[dict[str, Any]] = []

    for commit in commits:
        sha = str(commit["commit_sha1"])
        paths = _paths(repo, sha)
        license_paths = sorted(
            path
            for path in paths
            if PurePosixPath(path).name.lower() in LICENSE_NAMES
        )
        readme_paths = sorted(
            path
            for path in paths
            if PurePosixPath(path).name.lower() in README_NAMES
        )
        ground = _ground_truth_summary(paths)

        for path in license_paths:
            data = _blob_bytes(repo, sha, path)
            license_occurrences.append(
                {
                    "commit_sha1": sha,
                    "path": path,
                    "git_blob_sha1": _blob_sha(repo, sha, path),
                    "bytes": len(data),
                    "sha256": _sha256(data),
                }
            )
        for path in readme_paths:
            blob = _blob_sha(repo, sha, path)
            key = (path, blob)
            if key not in readme_versions:
                record = _readme_record(repo, sha, path)
                record["first_observed_commit_sha1"] = sha
                readme_versions[key] = record

        if ground["file_count"]:
            ground_versions.append({"commit_sha1": sha, **ground})
            gt_paths = [
                path
                for path in paths
                if path.startswith("ground_truth/") and path.lower().endswith(".arff")
            ]
            for path in gt_paths:
                first_seen.setdefault(path, sha)

        commit_summaries.append(
            {
                **commit,
                "tree_path_count": len(paths),
                "license_paths": license_paths,
                "readme_paths": readme_paths,
                "ground_truth_file_count": ground["file_count"],
                "ground_truth_token_count": ground["file_subject_token_count"],
                "ground_truth_clip_count": ground["clip_count"],
                "ground_truth_path_fingerprint_sha256": ground[
                    "path_fingerprint_sha256"
                ],
            }
        )

    latest_ground = ground_versions[-1] if ground_versions else None
    earliest_ground = ground_versions[0] if ground_versions else None
    current_paths = _paths(repo, str(commits[-1]["commit_sha1"]))
    current_ground = _ground_truth_summary(current_paths)
    first_seen_counts: dict[str, int] = {}
    for commit in first_seen.values():
        first_seen_counts[commit] = first_seen_counts.get(commit, 0) + 1

    readmes = sorted(
        readme_versions.values(),
        key=lambda item: (
            str(item["path"]),
            str(item["first_observed_commit_sha1"]),
        ),
    )
    unique_license_blobs = sorted(
        {
            (
                item["path"],
                item["git_blob_sha1"],
                item["sha256"],
                item["bytes"],
            )
            for item in license_occurrences
        }
    )
    license_blob_records = [
        {
            "path": path,
            "git_blob_sha1": blob,
            "sha256": digest,
            "bytes": size,
        }
        for path, blob, digest, size in unique_license_blobs
    ]

    token_sets = {tuple(version["file_subject_tokens"]) for version in ground_versions}
    path_fingerprints = {
        str(version["path_fingerprint_sha256"]) for version in ground_versions
    }
    return {
        "commit_count": len(commits),
        "initial_commit_sha1": commits[0]["commit_sha1"],
        "head_commit_sha1": commits[-1]["commit_sha1"],
        "commits": commit_summaries,
        "license_history": {
            "license_named_file_ever_present": bool(license_occurrences),
            "occurrence_count": len(license_occurrences),
            "unique_blob_count": len(license_blob_records),
            "unique_blobs": license_blob_records,
        },
        "readme_history": {
            "unique_version_count": len(readmes),
            "versions": readmes,
            "license_keyword_ever_present": any(
                any(
                    "license" in line.lower() or "licence" in line.lower()
                    for line in item["keyword_lines"]
                )
                for item in readmes
            ),
            "identity_keyword_ever_present": any(
                any(
                    word in line.lower()
                    for word in (
                        "subject",
                        "participant",
                        "observer",
                        "identity",
                    )
                )
                for item in readmes
                for line in item["keyword_lines"]
            ),
        },
        "ground_truth_history": {
            "commit_versions_with_ground_truth": len(ground_versions),
            "earliest": earliest_ground,
            "latest": latest_ground,
            "current": current_ground,
            "token_set_version_count": len(token_sets),
            "path_inventory_version_count": len(path_fingerprints),
            "all_current_paths_first_seen": len(first_seen) == current_ground["file_count"],
            "first_seen_commit_counts": dict(sorted(first_seen_counts.items())),
            "first_seen_fingerprint_sha256": _sha256(
                [
                    {"path": path, "commit_sha1": first_seen[path]}
                    for path in sorted(first_seen)
                ]
            ),
        },
    }


def probe(
    repository: str = REPOSITORY,
    *,
    pinned_head: str | None = PINNED_HEAD,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="hollywood2-gin-history-") as tmp:
        repo = Path(tmp) / "repo"
        _run(
            "git",
            "clone",
            "--filter=blob:none",
            "--no-checkout",
            repository,
            str(repo),
            timeout=1800,
        )
        head = _run("git", "rev-parse", "HEAD", cwd=repo).stdout.strip()
        if pinned_head is not None and head != pinned_head:
            raise RuntimeError(
                "Canonical Hollywood2EM GIN HEAD drifted from the reviewed revision: "
                f"expected={pinned_head}, observed={head}."
            )
        history = _history(repo, "HEAD")

    record: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "status": "verified-history-probe",
        "repository": repository,
        "pinned_head_sha1": pinned_head,
        "observed_head_sha1": head,
        "history": history,
        "scientific_boundary": {
            "repository_history_audited": True,
            "historical_license_named_file_search_completed": True,
            "historical_readme_keyword_search_completed": True,
            "ground_truth_path_history_audited": True,
            "filename_prefix_is_authoritative_participant_identity": False,
            "participant_group_membership_by_prefix_verified": False,
            "exact_license_identifier_verified": False,
            "redistribution_terms_verified": False,
            "participant_disjoint_model_validation_unlocked": False,
        },
    }
    record["probe_fingerprint_sha256"] = _fingerprint(record)
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default=REPOSITORY)
    parser.add_argument("--pinned-head", default=PINNED_HEAD)
    parser.add_argument("--output", default="hollywood2_gin_history_probe.json")
    args = parser.parse_args()
    pinned = args.pinned_head.strip() or None
    record = probe(args.repository, pinned_head=pinned)
    output = Path(args.output)
    output.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(record, sort_keys=True))


if __name__ == "__main__":
    main()
