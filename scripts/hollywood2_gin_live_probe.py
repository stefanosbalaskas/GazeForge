#!/usr/bin/env python3
"""Audit the canonical Hollywood2EM GIN repository without vendoring source bytes."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import statistics
import subprocess
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPOSITORY = "https://gin.g-node.org/ioannis.agtzidis/hollywood2_em.git"
RECORD_TYPE = "hollywood2-gin-live-probe-v2"
LICENSE_NAMES = {
    "license",
    "license.md",
    "license.txt",
    "copying",
    "copying.md",
    "copying.txt",
}
README_NAMES = {"readme", "readme.md", "readme.txt", "readme.rst"}
ATTRIBUTE_RE = re.compile(
    r"^@attribute\s+(?:'([^']+)'|\"([^\"]+)\"|(\S+))\s+(.+)$",
    flags=re.IGNORECASE,
)


def _run(
    *args: str,
    cwd: Path | None = None,
    timeout: int = 300,
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


def _git_blob_sha1(data: bytes) -> str:
    body = f"blob {len(data)}\0".encode() + data
    return hashlib.sha1(body).hexdigest()  # noqa: S324 - Git object identity requires SHA-1.


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


def _text_record(repo: Path, tree_record: dict[str, Any]) -> dict[str, Any]:
    path = repo / str(tree_record["path"])
    data = path.read_bytes()
    if _git_blob_sha1(data) != tree_record["git_object_sha1"]:
        raise RuntimeError(f"Git blob identity mismatch for {tree_record['path']}")
    return {
        "path": tree_record["path"],
        "git_object_sha1": tree_record["git_object_sha1"],
        "bytes": len(data),
        "sha256": _sha256_bytes(data),
        "text": data.decode("utf-8", errors="replace"),
    }


def _parse_attribute(line: str) -> tuple[str, str] | None:
    match = ATTRIBUTE_RE.match(line.strip())
    if not match:
        return None
    name = next(group for group in match.groups()[:3] if group is not None)
    return name, match.group(4).strip()


def _normalise_label(value: str) -> str:
    text = value.strip().strip("'\"")
    return text if text else "<empty>"


def _parse_ground_truth_arff(data: bytes) -> dict[str, Any]:
    text = data.decode("utf-8", errors="replace")
    attributes: list[tuple[str, str]] = []
    relation: str | None = None
    data_started = False
    rows = 0
    label_counts: dict[str, Counter[str]] = defaultdict(Counter)
    comparison_total = 0
    comparison_equal = 0
    confusion: Counter[str] = Counter()
    positive_deltas: list[float] = []
    previous_time: float | None = None
    coordinate_ranges = {
        "x": [None, None],
        "y": [None, None],
        "confidence": [None, None],
    }
    zero_pair_count = 0

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("%"):
            continue
        if not data_started:
            lowered = stripped.lower()
            if lowered.startswith("@relation"):
                relation = stripped[len("@relation") :].strip()
            elif lowered.startswith("@attribute"):
                parsed = _parse_attribute(stripped)
                if parsed is not None:
                    attributes.append(parsed)
            elif lowered == "@data":
                data_started = True
            continue

        values = next(csv.reader([raw_line], skipinitialspace=True))
        if len(values) != len(attributes):
            raise RuntimeError(
                f"ARFF data width {len(values)} does not match schema width {len(attributes)}"
            )
        rows += 1
        names = [name for name, _ in attributes]
        index = {name: position for position, name in enumerate(names)}

        for label_name in ("handlabeller_1", "handlabeller_final"):
            if label_name in index:
                label_counts[label_name][_normalise_label(values[index[label_name]])] += 1

        if "handlabeller_1" in index and "handlabeller_final" in index:
            first = _normalise_label(values[index["handlabeller_1"]])
            final = _normalise_label(values[index["handlabeller_final"]])
            comparison_total += 1
            comparison_equal += int(first == final)
            confusion[f"{first}->{final}"] += 1

        if "time" in index:
            try:
                current_time = float(values[index["time"]])
            except ValueError:
                current_time = None
            if current_time is not None and previous_time is not None:
                delta = current_time - previous_time
                if delta > 0:
                    positive_deltas.append(delta)
            if current_time is not None:
                previous_time = current_time

        numeric: dict[str, float | None] = {}
        for name in ("x", "y", "confidence"):
            if name not in index:
                numeric[name] = None
                continue
            try:
                number = float(values[index[name]])
            except ValueError:
                numeric[name] = None
                continue
            numeric[name] = number
            low, high = coordinate_ranges[name]
            coordinate_ranges[name] = [
                number if low is None else min(float(low), number),
                number if high is None else max(float(high), number),
            ]
        if numeric.get("x") == 0.0 and numeric.get("y") == 0.0:
            zero_pair_count += 1

    names = [name for name, _ in attributes]
    median_delta = statistics.median(positive_deltas) if positive_deltas else None
    inferred_rate = 1_000_000.0 / median_delta if median_delta else None
    return {
        "relation": relation,
        "attributes": [{"name": name, "type": kind} for name, kind in attributes],
        "attribute_names": names,
        "row_count": rows,
        "label_counts": {key: dict(sorted(value.items())) for key, value in label_counts.items()},
        "student_final_comparison": {
            "sample_count": comparison_total,
            "equal_sample_count": comparison_equal,
            "changed_sample_count": comparison_total - comparison_equal,
            "raw_agreement_fraction": (
                comparison_equal / comparison_total if comparison_total else None
            ),
            "confusion": dict(sorted(confusion.items())),
        },
        "median_positive_time_delta": median_delta,
        "inferred_sampling_rate_hz_assuming_time_us": inferred_rate,
        "observed_numeric_ranges": coordinate_ranges,
        "zero_xy_pair_count": zero_pair_count,
    }


def _ground_truth_audit(repo: Path, tree: list[dict[str, Any]]) -> dict[str, Any]:
    ground_truth = [
        item
        for item in tree
        if str(item["path"]).startswith("ground_truth/")
        and str(item["path"]).lower().endswith(".arff")
    ]
    ledger: list[dict[str, Any]] = []
    split_counts: Counter[str] = Counter()
    participants: set[str] = set()
    clips: set[str] = set()
    schema_signatures: Counter[str] = Counter()
    relation_counts: Counter[str] = Counter()
    total_rows = 0
    total_bytes = 0
    total_comparison = 0
    total_equal = 0
    total_zero_pairs = 0
    global_labels: dict[str, Counter[str]] = defaultdict(Counter)
    global_confusion: Counter[str] = Counter()
    file_rates: list[float] = []
    ranges: dict[str, list[float | None]] = {
        "x": [None, None],
        "y": [None, None],
        "confidence": [None, None],
    }

    for item in ground_truth:
        relative = str(item["path"])
        parts = Path(relative).parts
        split = parts[1] if len(parts) > 1 else "unknown"
        clip = parts[2] if len(parts) > 2 else "unknown"
        participant = Path(relative).name.split("_", 1)[0]
        data = (repo / relative).read_bytes()
        computed_blob = _git_blob_sha1(data)
        if computed_blob != item["git_object_sha1"]:
            raise RuntimeError(f"Git blob identity mismatch for {relative}")
        parsed = _parse_ground_truth_arff(data)
        attributes = parsed["attributes"]
        schema_signature = _sha256_bytes(_canonical_bytes({"attributes": attributes}))
        schema_signatures[schema_signature] += 1
        relation_counts[str(parsed["relation"])] += 1
        split_counts[split] += 1
        participants.add(participant)
        clips.add(clip)
        total_rows += int(parsed["row_count"])
        total_bytes += len(data)
        comparison = parsed["student_final_comparison"]
        total_comparison += int(comparison["sample_count"])
        total_equal += int(comparison["equal_sample_count"])
        total_zero_pairs += int(parsed["zero_xy_pair_count"])
        for column, counts in parsed["label_counts"].items():
            global_labels[column].update(counts)
        global_confusion.update(comparison["confusion"])
        rate = parsed["inferred_sampling_rate_hz_assuming_time_us"]
        if rate is not None:
            file_rates.append(float(rate))
        for name, observed in parsed["observed_numeric_ranges"].items():
            if observed[0] is None:
                continue
            low, high = ranges[name]
            ranges[name] = [
                observed[0] if low is None else min(float(low), float(observed[0])),
                observed[1] if high is None else max(float(high), float(observed[1])),
            ]
        ledger.append(
            {
                "path": relative,
                "split": split,
                "clip_id": clip,
                "file_subject_token": participant,
                "bytes": len(data),
                "git_blob_sha1": computed_blob,
                "sha256": _sha256_bytes(data),
                "row_count": parsed["row_count"],
                "schema_signature_sha256": schema_signature,
                "median_positive_time_delta": parsed["median_positive_time_delta"],
                "inferred_sampling_rate_hz_assuming_time_us": rate,
            }
        )

    representative: dict[str, Any] | None = None
    if ground_truth:
        first = ground_truth[0]
        data = (repo / str(first["path"])).read_bytes()
        parsed = _parse_ground_truth_arff(data)
        representative = {
            "path": first["path"],
            "git_blob_sha1": first["git_object_sha1"],
            "sha256": _sha256_bytes(data),
            "bytes": len(data),
            "relation": parsed["relation"],
            "attributes": parsed["attributes"],
            "row_count": parsed["row_count"],
            "label_counts": parsed["label_counts"],
            "student_final_comparison": parsed["student_final_comparison"],
            "median_positive_time_delta": parsed["median_positive_time_delta"],
            "inferred_sampling_rate_hz_assuming_time_us": parsed[
                "inferred_sampling_rate_hz_assuming_time_us"
            ],
            "observed_numeric_ranges": parsed["observed_numeric_ranges"],
            "zero_xy_pair_count": parsed["zero_xy_pair_count"],
        }

    return {
        "file_count": len(ground_truth),
        "total_bytes": total_bytes,
        "total_rows": total_rows,
        "splits": dict(sorted(split_counts.items())),
        "clip_count": len(clips),
        "clip_ids": sorted(clips),
        "file_subject_token_count": len(participants),
        "file_subject_tokens": sorted(participants),
        "schema_signatures": dict(sorted(schema_signatures.items())),
        "relations": dict(sorted(relation_counts.items())),
        "global_label_counts": {
            key: dict(sorted(value.items())) for key, value in global_labels.items()
        },
        "student_final_comparison": {
            "sample_count": total_comparison,
            "equal_sample_count": total_equal,
            "changed_sample_count": total_comparison - total_equal,
            "raw_agreement_fraction": total_equal / total_comparison if total_comparison else None,
            "confusion": dict(sorted(global_confusion.items())),
            "independent_human_human_agreement": False,
            "interpretation": "first/student coding versus expert-corrected final coding",
        },
        "sampling_rate": {
            "files_with_positive_time_deltas": len(file_rates),
            "median_file_rate_hz_assuming_time_us": statistics.median(file_rates)
            if file_rates
            else None,
            "minimum_file_rate_hz_assuming_time_us": min(file_rates) if file_rates else None,
            "maximum_file_rate_hz_assuming_time_us": max(file_rates) if file_rates else None,
            "time_unit_semantics_verified_from_repository": False,
        },
        "observed_numeric_ranges": ranges,
        "zero_xy_pair_count": total_zero_pairs,
        "representative_file": representative,
        "source_identity_ledger": ledger,
    }


def probe(repository: str = REPOSITORY) -> dict[str, Any]:
    remote_result = _run(
        "git",
        "ls-remote",
        "--symref",
        repository,
        "HEAD",
        "refs/heads/*",
        "refs/tags/*",
    )
    remote = _parse_ls_remote(remote_result.stdout)
    if not remote.get("head_sha"):
        raise RuntimeError("GIN repository did not expose a resolvable HEAD SHA.")

    with tempfile.TemporaryDirectory(prefix="gazeforge-hollywood2-gin-") as temp_dir:
        repo = Path(temp_dir) / "hollywood2_em"
        _run("git", "clone", "--depth", "1", repository, str(repo), timeout=600)
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
            _text_record(repo, item)
            for item in tree
            if Path(str(item["path"])).name.lower() in LICENSE_NAMES
            and item["mode"] != "120000"
        ]
        readme_records = [
            _text_record(repo, item)
            for item in tree
            if Path(str(item["path"])).name.lower() in README_NAMES
            and item["mode"] != "120000"
        ]
        ground_truth = _ground_truth_audit(repo, tree)

    top_level_counts: Counter[str] = Counter(str(item["path"]).split("/", 1)[0] for item in tree)
    record: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "status": "verified_authoritative_source_probe",
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
            "arff_path_count": sum(
                1 for item in tree if str(item["path"]).lower().endswith(".arff")
            ),
            "total_git_object_bytes": sum(
                int(item["git_object_bytes"] or 0) for item in tree
            ),
            "top_level_entry_counts": dict(sorted(top_level_counts.items())),
        },
        "license_files": license_records,
        "readme_files": readme_records,
        "ground_truth": ground_truth,
        "scientific_boundary": {
            "authoritative_repository_revision_resolved": True,
            "authoritative_ground_truth_blobs_recovered": ground_truth["file_count"] > 0,
            "ground_truth_source_identity_ledger_created": ground_truth["file_count"] > 0,
            "repository_license_file_recovered": bool(license_records),
            "dataset_license_verified": False,
            "full_original_hollywood2_video_dataset_recovered": False,
            "file_subject_tokens_recovered": ground_truth["file_subject_token_count"] > 0,
            "participant_identity_mapping_verified": False,
            "coordinate_unit_verified": False,
            "time_unit_verified_from_repository": False,
            "student_vs_expert_corrected_sensitivity_created": ground_truth[
                "student_final_comparison"
            ]["sample_count"]
            > 0,
            "independent_human_human_agreement_created": False,
            "model_validation_created": False,
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
    summary = {
        "head": record["head"]["commit_sha1"],
        "default_ref": record["remote"]["default_ref"],
        "tree_entries": record["tree"]["entry_count"],
        "arff_paths": record["tree"]["arff_path_count"],
        "ground_truth_files": record["ground_truth"]["file_count"],
        "ground_truth_rows": record["ground_truth"]["total_rows"],
        "ground_truth_clips": record["ground_truth"]["clip_count"],
        "file_subject_tokens": record["ground_truth"]["file_subject_token_count"],
        "student_final_raw_agreement": record["ground_truth"]["student_final_comparison"][
            "raw_agreement_fraction"
        ],
        "license_files": [item["path"] for item in record["license_files"]],
        "probe_fingerprint_sha256": record["probe_fingerprint_sha256"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
