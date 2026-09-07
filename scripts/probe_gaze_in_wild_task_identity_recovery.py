"""Probe pinned first-party GIW sources for explicit task-to-trial identity evidence.

This is a source-recovery probe, not an inference engine.  It records task-related
contexts from the exact first-author repository revision and keeps the scientific
mapping gate closed unless an explicit mapping is present for later human review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path
from typing import Any

PINNED_COMMIT = "52262d44e366a53369e10ca73c5f41daf0e8f1e5"
CANONICAL_REPOSITORY = "https://github.com/RSKothari/Gaze-in-Wild"
MLAPP_PATH = "GIWApp.mlapp"
MLAPP_BLOB_SHA1 = "2d560af336af637e042ea7a96f4c3736a59d2a2f"
TASK_RE = re.compile(
    r"(?i)(indoor[_ -]?(?:walk|navigation)|ball[_ -]?catch(?:ing)?|"
    r"visual[_ -]?search|tea[_ -]?(?:making|make)|GIW_rearranged)"
)
IDENTITY_RE = re.compile(r"(?i)\b(?:PrIdx|TrIdx)\b")
TRIDX_ASSIGN_RE = re.compile(r"(?i)\bTrIdx\s*=\s*(\d+)\b")
PRINTABLE_RE = re.compile(rb"[\x20-\x7e]{4,}")


class ProbeError(RuntimeError):
    pass


def _run(root: Path, *args: str, binary: bool = False) -> bytes | str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, check=False
    )
    if result.returncode:
        raise ProbeError(
            result.stderr.decode("utf-8", errors="replace").strip()
            or f"git {' '.join(args)} failed"
        )
    return result.stdout if binary else result.stdout.decode("utf-8", errors="strict")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _normalise_origin(value: str) -> str:
    value = value.strip().removesuffix(".git").rstrip("/")
    if value.startswith("git@github.com:"):
        value = "https://github.com/" + value.removeprefix("git@github.com:")
    return value


def _redact_context(text: str) -> str:
    text = re.sub(
        r"(?i)(?:/[A-Za-z0-9_.:,=@+-]+){2,}/(?=(?:GIW_rearranged|Indoor|Ball|Visual|Tea))",
        "<absolute-prefix>/",
        text,
    )
    return " ".join(text.split())[:500]


def _context_windows(text: str, source: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    rows: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()
    for idx, line in enumerate(lines):
        if not TASK_RE.search(line):
            continue
        lo, hi = max(0, idx - 5), min(len(lines), idx + 6)
        context = "\n".join(lines[lo:hi])
        tridx = sorted({int(x) for x in TRIDX_ASSIGN_RE.findall(context)})
        row = {
            "source": source,
            "task_hit_line": idx + 1,
            "task_terms": sorted({m.group(0).lower() for m in TASK_RE.finditer(context)}),
            "contains_identity_token": bool(IDENTITY_RE.search(context)),
            "nearby_tridx_assignments": tridx,
            "context": _redact_context(context),
        }
        key = (idx + 1, row["context"])
        if key not in seen:
            seen.add(key)
            rows.append(row)
    return rows


def _mlapp_audit(root: Path) -> dict[str, Any]:
    blob = _run(root, "rev-parse", f"HEAD:{MLAPP_PATH}").strip()
    if blob != MLAPP_BLOB_SHA1:
        raise ProbeError(f"GIWApp blob drifted: {blob}")
    raw = _run(root, "show", f"HEAD:{MLAPP_PATH}", binary=True)
    assert isinstance(raw, bytes)
    member_rows: list[dict[str, Any]] = []
    contexts: list[dict[str, Any]] = []
    if zipfile.is_zipfile(Path(root / MLAPP_PATH)):
        # The checked-out file is byte-identical to the blob verified above.
        with zipfile.ZipFile(root / MLAPP_PATH) as zf:
            bad = zf.testzip()
            if bad is not None:
                raise ProbeError(f"GIWApp archive CRC failed at {bad}")
            for info in sorted(zf.infolist(), key=lambda x: x.filename):
                if info.is_dir():
                    continue
                data = zf.read(info)
                member_rows.append(
                    {
                        "name": info.filename,
                        "size": info.file_size,
                        "sha256": _sha256_bytes(data),
                    }
                )
                decoded = data.decode("utf-8", errors="ignore")
                if TASK_RE.search(decoded):
                    contexts.extend(_context_windows(decoded, f"mlapp:{info.filename}"))
                # Some MLAPP payloads contain printable strings inside binary members.
                printable = "\n".join(
                    chunk.decode("ascii", errors="ignore") for chunk in PRINTABLE_RE.findall(data)
                )
                if TASK_RE.search(printable):
                    contexts.extend(_context_windows(printable, f"mlapp-strings:{info.filename}"))
    else:
        printable = "\n".join(
            chunk.decode("ascii", errors="ignore") for chunk in PRINTABLE_RE.findall(raw)
        )
        contexts.extend(_context_windows(printable, "mlapp-strings:GIWApp.mlapp"))

    # Dedupe contexts generated through UTF-8 and printable-string passes.
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for row in contexts:
        unique[(row["source"], row["context"])] = row
    return {
        "path": MLAPP_PATH,
        "git_blob_sha1": blob,
        "size_bytes": len(raw),
        "sha256": _sha256_bytes(raw),
        "zip_container": bool(member_rows),
        "members": member_rows,
        "task_contexts": sorted(unique.values(), key=lambda r: (r["source"], r["task_hit_line"])),
    }


def _history_task_contexts(root: Path) -> dict[str, Any]:
    commits = [x for x in _run(root, "rev-list", "--reverse", "HEAD").splitlines() if x]
    unique_blobs: dict[str, tuple[str, str]] = {}
    for commit in commits:
        paths = [
            x
            for x in _run(root, "ls-tree", "-r", "--name-only", commit).splitlines()
            if x.lower().endswith((".m", ".py", ".md", ".txt", ".json", ".csv"))
        ]
        for path in paths:
            blob = _run(root, "rev-parse", f"{commit}:{path}").strip()
            unique_blobs.setdefault(blob, (commit, path))

    contexts: list[dict[str, Any]] = []
    task_blob_count = 0
    for blob, (commit, path) in sorted(unique_blobs.items()):
        raw = _run(root, "cat-file", "blob", blob, binary=True)
        assert isinstance(raw, bytes)
        text = raw.decode("utf-8", errors="ignore")
        if not TASK_RE.search(text):
            continue
        task_blob_count += 1
        for row in _context_windows(text, f"history:{path}"):
            row["representative_commit_sha1"] = commit
            row["git_blob_sha1"] = blob
            contexts.append(row)

    return {
        "reachable_commit_count": len(commits),
        "unique_text_blob_count": len(unique_blobs),
        "task_related_blob_count": task_blob_count,
        "task_contexts": contexts,
    }


def build_probe(root: Path) -> dict[str, Any]:
    root = root.resolve()
    head = _run(root, "rev-parse", "HEAD").strip()
    if head != PINNED_COMMIT:
        raise ProbeError(f"Expected pinned commit {PINNED_COMMIT}, observed {head}")
    origin = _normalise_origin(_run(root, "remote", "get-url", "origin"))
    if origin != CANONICAL_REPOSITORY:
        raise ProbeError(f"Unexpected origin: {origin}")

    mlapp = _mlapp_audit(root)
    history = _history_task_contexts(root)
    candidate_contexts = mlapp["task_contexts"] + history["task_contexts"]
    explicit_candidate_count = sum(
        bool(row["contains_identity_token"] and row["nearby_tridx_assignments"])
        for row in candidate_contexts
    )
    record: dict[str, Any] = {
        "record_type": "gaze-in-wild-task-identity-recovery-probe-v1",
        "source": {"repository": CANONICAL_REPOSITORY, "commit_sha1": PINNED_COMMIT},
        "mlapp": mlapp,
        "reachable_history": history,
        "review_queue": {
            "task_context_count": len(candidate_contexts),
            "identity_plus_tridx_candidate_context_count": explicit_candidate_count,
            "candidate_contexts_require_human_semantic_review": True,
        },
        "scientific_boundary": {
            "universal_tridx_to_task_mapping_verified": False,
            "complete_per_file_task_mapping_verified": False,
            "participant_disjoint_model_validation_created": False,
            "cross_dataset_validation_created": False,
            "new_empirical_performance_claim_created": False,
        },
    }
    body = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    record["probe_fingerprint_sha256"] = hashlib.sha256(body).hexdigest()
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("repository")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    record = build_probe(Path(args.repository))
    Path(args.output).write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("probe_fingerprint_sha256", record["probe_fingerprint_sha256"])
    print("task_context_count", record["review_queue"]["task_context_count"])
    print(
        "identity_plus_tridx_candidate_context_count",
        record["review_queue"]["identity_plus_tridx_candidate_context_count"],
    )


if __name__ == "__main__":
    main()
