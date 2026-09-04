#!/usr/bin/env python3
"""Probe the canonical Hollywood2EM GIN repository without vendoring dataset bytes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

REPOSITORY = "https://gin.g-node.org/ioannis.agtzidis/hollywood2_em.git"
RECORD_TYPE = "hollywood2-gin-live-probe-v1"
ANNEX_SIZE_RE = re.compile(r"-s(?P<size>\d+)--")
LICENSE_NAMES = {
    "license",
    "license.md",
    "license.txt",
    "copying",
    "copying.md",
    "copying.txt",
}
README_NAMES = {"readme", "readme.md", "readme.txt", "readme.rst"}


def _run(
    *args: str,
    cwd: Path | None = None,
    timeout: int = 180,
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


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _probe_fingerprint(payload: dict[str, Any]) -> str:
    body = {key: value for key, value in payload.items() if key != "probe_fingerprint_sha256"}
    return _sha256_bytes(_canonical_bytes(body))


def _parse_ls_remote(text: str) -> dict[str, Any]:
    default_ref: str | None = None
    refs: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("ref:"):
            left, right = line.split("\t", 1)
            if right == "HEAD":
                default_ref = left.split()[1]
            continue
        try:
            sha, ref = line.split("\t", 1)
        except ValueError:
            continue
        refs[ref] = sha
    return {
        "default_ref": default_ref,
        "head_sha": refs.get("HEAD"),
        "heads": {key: refs[key] for key in sorted(refs) if key.startswith("refs/heads/")},
        "tags": {key: refs[key] for key in sorted(refs) if key.startswith("refs/tags/")},
    }


def _parse_tree(text: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for raw_line in text.splitlines():
        if not raw_line.strip():
            continue
        metadata, path = raw_line.split("\t", 1)
        mode, obj_type, sha, size_text = metadata.split(" ", 3)
        records.append(
            {
                "path": path,
                "mode": mode,
                "type": obj_type,
                "git_object_sha1": sha,
                "git_object_bytes": None if size_text == "-" else int(size_text),
            }
        )
    return records


def _git_show_bytes(repo: Path, revision: str, path: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Could not read {path!r} at {revision}: "
            f"{result.stderr.decode('utf-8', errors='replace')}"
        )
    return result.stdout


def _text_record(repo: Path, revision: str, tree_record: dict[str, Any]) -> dict[str, Any]:
    data = _git_show_bytes(repo, revision, str(tree_record["path"]))
    text = data.decode("utf-8", errors="replace")
    return {
        "path": tree_record["path"],
        "git_object_sha1": tree_record["git_object_sha1"],
        "bytes": len(data),
        "sha256": _sha256_bytes(data),
        "text": text,
    }


def _annex_key_from_target(target: str) -> str | None:
    normalized = target.replace("\\", "/").strip()
    if "/annex/objects/" not in normalized:
        return None
    parts = [part for part in normalized.split("/") if part]
    if not parts:
        return None
    candidate = parts[-1]
    return candidate if "--" in candidate else None


def _annex_size(key: str | None) -> int | None:
    if not key:
        return None
    match = ANNEX_SIZE_RE.search(key)
    return int(match.group("size")) if match else None


def _inspect_annex_entries(
    repo: Path,
    revision: str,
    tree: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in tree:
        if item["mode"] != "120000":
            continue
        target = _git_show_bytes(repo, revision, str(item["path"])).decode(
            "utf-8", errors="replace"
        ).strip()
        key = _annex_key_from_target(target)
        records.append(
            {
                "path": item["path"],
                "git_symlink_blob_sha1": item["git_object_sha1"],
                "symlink_target": target,
                "annex_key": key,
                "annex_key_bytes": _annex_size(key),
            }
        )
    return records


def _parse_json_lines(text: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            records.append({"raw": line})
        else:
            records.append(value if isinstance(value, dict) else {"value": value})
    return records


def _probe_annex_payload(repo: Path, annex_entries: list[dict[str, Any]]) -> dict[str, Any]:
    git_annex = shutil.which("git-annex") or shutil.which("git")
    version = _run("git", "annex", "version", cwd=repo, check=False)
    available = version.returncode == 0
    result: dict[str, Any] = {
        "git_annex_available": available,
        "git_annex_executable_hint": git_annex,
        "version_stdout": version.stdout.strip(),
        "version_stderr": version.stderr.strip(),
        "candidate": None,
        "whereis": [],
        "get": [],
        "payload_recovered": False,
    }
    if not available:
        return result

    candidates = [
        item
        for item in annex_entries
        if str(item["path"]).lower().endswith(".arff")
        and isinstance(item.get("annex_key_bytes"), int)
        and int(item["annex_key_bytes"]) <= 25_000_000
    ]
    candidates.sort(key=lambda item: (int(item["annex_key_bytes"]), str(item["path"])))
    if not candidates:
        return result

    candidate = candidates[0]
    path = str(candidate["path"])
    result["candidate"] = {
        "path": path,
        "annex_key": candidate["annex_key"],
        "annex_key_bytes": candidate["annex_key_bytes"],
    }

    whereis = _run("git", "annex", "whereis", "--json", "--", path, cwd=repo, check=False)
    result["whereis"] = _parse_json_lines(whereis.stdout)
    result["whereis_returncode"] = whereis.returncode
    result["whereis_stderr"] = whereis.stderr.strip()

    get = _run("git", "annex", "get", "--json", "--", path, cwd=repo, timeout=300, check=False)
    result["get"] = _parse_json_lines(get.stdout)
    result["get_returncode"] = get.returncode
    result["get_stderr"] = get.stderr.strip()

    payload = repo / path
    if get.returncode == 0 and payload.exists() and payload.is_file():
        data = payload.read_bytes()
        result["payload_recovered"] = True
        result["payload"] = {
            "path": path,
            "bytes": len(data),
            "sha256": _sha256_bytes(data),
            "annex_key": candidate["annex_key"],
        }
        if path.lower().endswith(".arff"):
            preview = data[:200_000].decode("utf-8", errors="replace")
            attributes = [
                line.strip()
                for line in preview.splitlines()
                if line.lstrip().lower().startswith("@attribute")
            ]
            result["payload"]["arff_attributes"] = attributes
            result["payload"]["contains_handlabeller_1"] = "handlabeller_1" in preview
            result["payload"]["contains_handlabeller_final"] = "handlabeller_final" in preview
    return result


def probe(repository: str = REPOSITORY) -> dict[str, Any]:
    ls_remote = _run("git", "ls-remote", "--symref", repository, "HEAD", "refs/heads/*", "refs/tags/*")
    remote = _parse_ls_remote(ls_remote.stdout)
    if not remote.get("head_sha"):
        raise RuntimeError("GIN repository did not expose a resolvable HEAD SHA.")

    with tempfile.TemporaryDirectory(prefix="gazeforge-hollywood2-gin-") as temp_dir:
        root = Path(temp_dir)
        repo = root / "hollywood2_em"
        _run("git", "clone", "--depth", "1", repository, str(repo), timeout=300)
        head_sha = _run("git", "rev-parse", "HEAD", cwd=repo).stdout.strip()
        if head_sha != remote["head_sha"]:
            raise RuntimeError(
                "GIN HEAD changed between ls-remote and clone; refusing a mixed-revision probe."
            )

        commit_fields = _run(
            "git",
            "show",
            "-s",
            "--format=%H%n%aI%n%cI%n%an%n%ae%n%cn%n%ce%n%B",
            "HEAD",
            cwd=repo,
        ).stdout.splitlines()
        tree = _parse_tree(_run("git", "ls-tree", "-r", "--long", "HEAD", cwd=repo).stdout)
        license_records = [
            _text_record(repo, head_sha, item)
            for item in tree
            if Path(str(item["path"])).name.lower() in LICENSE_NAMES and item["mode"] != "120000"
        ]
        readme_records = [
            _text_record(repo, head_sha, item)
            for item in tree
            if Path(str(item["path"])).name.lower() in README_NAMES and item["mode"] != "120000"
        ]
        attribute_records = [
            _text_record(repo, head_sha, item)
            for item in tree
            if Path(str(item["path"])).name == ".gitattributes" and item["mode"] != "120000"
        ]
        annex_entries = _inspect_annex_entries(repo, head_sha, tree)
        annex_probe = _probe_annex_payload(repo, annex_entries)

    record: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "status": "source_probe_only",
        "repository": repository,
        "remote": remote,
        "head": {
            "commit_sha1": head_sha,
            "author_date": commit_fields[1] if len(commit_fields) > 1 else None,
            "committer_date": commit_fields[2] if len(commit_fields) > 2 else None,
            "author_name": commit_fields[3] if len(commit_fields) > 3 else None,
            "author_email": commit_fields[4] if len(commit_fields) > 4 else None,
            "committer_name": commit_fields[5] if len(commit_fields) > 5 else None,
            "committer_email": commit_fields[6] if len(commit_fields) > 6 else None,
            "message": "\n".join(commit_fields[7:]).strip(),
        },
        "tree": {
            "entry_count": len(tree),
            "regular_blob_count": sum(1 for item in tree if item["mode"] != "120000"),
            "symlink_count": sum(1 for item in tree if item["mode"] == "120000"),
            "arff_path_count": sum(1 for item in tree if str(item["path"]).lower().endswith(".arff")),
            "paths": [item["path"] for item in tree],
        },
        "license_files": license_records,
        "readme_files": readme_records,
        "gitattributes_files": attribute_records,
        "annex": {
            "entry_count": len(annex_entries),
            "arff_entry_count": sum(
                1 for item in annex_entries if str(item["path"]).lower().endswith(".arff")
            ),
            "entries": annex_entries,
            "payload_probe": annex_probe,
        },
        "scientific_boundary": {
            "authoritative_repository_revision_resolved": True,
            "dataset_license_verified": bool(license_records),
            "representative_payload_recovered": bool(annex_probe.get("payload_recovered")),
            "full_dataset_recovered": False,
            "participant_identity_mapping_verified": False,
            "coordinate_unit_verified": False,
            "empirical_metrics_created": False,
            "source_bytes_redistributed_by_gazeforge": False,
        },
    }
    record["probe_fingerprint_sha256"] = _probe_fingerprint(record)
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=REPOSITORY)
    parser.add_argument("--output", default="hollywood2_gin_live_probe.json")
    args = parser.parse_args()
    record = probe(args.repository)
    output = Path(args.output)
    output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
