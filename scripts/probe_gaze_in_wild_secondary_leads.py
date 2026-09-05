"""Audit immutable secondary Gaze-in-the-Wild recovery leads without promotion."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

AWESOME_REPOSITORY = "https://github.com/Morris88826/awesome-eye-data"
AWESOME_COMMIT = "4c6a58ef5be5693e08adac33e8768a3b88ddf8ac"
AWESOME_TREE = "b91211698b0a9d95f142a3a90d229a4d3d642f9c"
AWESOME_README_BLOB = "1c5be77e40928b8a755450452824f7d85f8badf1"
AWESOME_DRIVE_URL = (
    "https://drive.google.com/drive/folders/1JZpXaR66MXBPIshuhSwY22wwnb1hQM7l?usp=sharing"
)

EDIT_REPOSITORY = "https://github.com/George614/edit_distance_gpu"
EDIT_COMMIT = "01711b11556c271a7a15e566935089bb2775121b"
EDIT_TREE = "9783f2af0e828f567d04ed82a0c1e80bf5a76774"
EDIT_DEMO_BLOB = "d0b0ca6ec9af468b1ada3c7243339889f076c3ee"
LABELLER_FILENAMES = (
    "LabellerIdx_7_PrIdx_1_TrIdx_1.mat",
    "LabellerIdx_8_PrIdx_1_TrIdx_1.mat",
)

_OFFICIAL_LAYOUT_RE = re.compile(
    r"(?:^|/)(?:ProcessData|LabelData)(?:/|$)|"
    r"(?:^|/)(?:PrIdx_\d+_TrIdx_\d+|LabellerIdx_\d+_PrIdx_\d+_TrIdx_\d+)\.mat$",
    re.I,
)


class ProbeError(RuntimeError):
    """Raised when a pinned secondary lead no longer matches the reviewed contract."""


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], check=False, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise ProbeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.rstrip("\n")


def _normalise_origin(value: str) -> str:
    origin = value.strip().removesuffix(".git").rstrip("/")
    if origin.startswith("git@github.com:"):
        origin = "https://github.com/" + origin.removeprefix("git@github.com:")
    return origin


def _verify_checkout(root: Path, *, repository: str, commit: str, tree: str) -> None:
    if not (root / ".git").exists():
        raise ProbeError(f"{root} must be a full Git checkout.")
    if _git(root, "rev-parse", "HEAD") != commit:
        raise ProbeError(f"Pinned commit mismatch for {repository}.")
    if _git(root, "rev-parse", "HEAD^{tree}") != tree:
        raise ProbeError(f"Pinned tree mismatch for {repository}.")
    if _normalise_origin(_git(root, "remote", "get-url", "origin")) != repository:
        raise ProbeError(f"Origin mismatch for {repository}.")
    if _git(root, "status", "--porcelain", "--untracked-files=no"):
        raise ProbeError(f"Tracked working-tree changes found for {repository}.")


def _paths(root: Path) -> list[str]:
    return [
        line
        for line in _git(root, "ls-tree", "-r", "--name-only", "HEAD").splitlines()
        if line
    ]


def _blob(root: Path, path: str) -> str:
    return _git(root, "rev-parse", f"HEAD:{path}")


def _text(root: Path, path: str) -> str:
    return _git(root, "show", f"HEAD:{path}")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def probe_fingerprint(record: dict[str, Any]) -> str:
    body = dict(record)
    body.pop("probe_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def build_probe(awesome_root: Path, edit_root: Path) -> dict[str, Any]:
    _verify_checkout(
        awesome_root,
        repository=AWESOME_REPOSITORY,
        commit=AWESOME_COMMIT,
        tree=AWESOME_TREE,
    )
    _verify_checkout(
        edit_root,
        repository=EDIT_REPOSITORY,
        commit=EDIT_COMMIT,
        tree=EDIT_TREE,
    )

    awesome_paths = _paths(awesome_root)
    edit_paths = _paths(edit_root)
    awesome_official = sorted(path for path in awesome_paths if _OFFICIAL_LAYOUT_RE.search(path))
    edit_official = sorted(path for path in edit_paths if _OFFICIAL_LAYOUT_RE.search(path))
    if awesome_official or edit_official:
        raise ProbeError("Pinned secondary repository unexpectedly contains official-layout files.")

    if _blob(awesome_root, "README.md") != AWESOME_README_BLOB:
        raise ProbeError("awesome-eye-data README blob drifted.")
    awesome_readme = _text(awesome_root, "README.md")
    required_awesome = (
        "A curated collection of real-world eye tracking datasets unified under a common format",
        "| **GazeinTheWild** | Eye and head coordination data captured during everyday activities |",
        f"Processed data is available for download on [Google Drive]({AWESOME_DRIVE_URL})",
        "ANNOTATIONS/   # CSV files (one per chunk)",
        "VIDEOS/        # Chunked eye video clips (.mp4)",
    )
    if not all(value in awesome_readme for value in required_awesome):
        raise ProbeError("awesome-eye-data reviewed README statements drifted.")

    if _blob(edit_root, "levenGPU_demo.py") != EDIT_DEMO_BLOB:
        raise ProbeError("edit_distance_gpu demo blob drifted.")
    edit_demo = _text(edit_root, "levenGPU_demo.py")
    if not all(name in edit_demo for name in LABELLER_FILENAMES):
        raise ProbeError("Reviewed labeller filename references drifted.")
    tracked_basenames = {Path(path).name for path in edit_paths}
    if any(name in tracked_basenames for name in LABELLER_FILENAMES):
        raise ProbeError("Referenced labeller file unexpectedly became repository-resident.")

    payload: dict[str, Any] = {
        "record_type": "gaze-in-wild-secondary-recovery-lead-provenance-probe-v1",
        "dataset": "Gaze-in-the-Wild",
        "sources": {
            "transformed_collection_lead": {
                "repository": AWESOME_REPOSITORY,
                "pinned_commit_sha1": AWESOME_COMMIT,
                "pinned_tree_sha1": AWESOME_TREE,
                "readme_blob_sha1": AWESOME_README_BLOB,
                "classification": "external_transformed_collection_advertisement",
                "gaze_in_the_wild_named": True,
                "common_format_transformation_declared": True,
                "external_processed_collection_url": AWESOME_DRIVE_URL,
                "advertised_annotation_representation": "CSV files (one per chunk)",
                "advertised_video_representation": "chunked MP4 eye video clips",
                "tracked_official_process_or_label_paths": [],
                "external_collection_contents_obtained_by_this_probe": False,
                "external_collection_contents_audited_by_this_probe": False,
                "authoritative_original_distribution_equivalence_verified": False,
            },
            "labeller_filename_lead": {
                "repository": EDIT_REPOSITORY,
                "pinned_commit_sha1": EDIT_COMMIT,
                "pinned_tree_sha1": EDIT_TREE,
                "demo_blob_sha1": EDIT_DEMO_BLOB,
                "classification": "local_path_reference_only",
                "referenced_labeller_filenames": list(LABELLER_FILENAMES),
                "referenced_labeller_files_repository_resident": False,
                "tracked_official_process_or_label_paths": [],
                "independent_annotation_streams_recovered": False,
                "human_human_agreement_eligible": False,
            },
        },
        "scientific_boundary": {
            "authoritative_original_dataset_copy_obtained": False,
            "original_distribution_identity_verified_from_secondary_leads": False,
            "dataset_file_rights_resolved": False,
            "analysis_use_authorized": False,
            "redistribution_authorized": False,
            "participant_mapping_verified": False,
            "complete_trial_task_mapping_verified": False,
            "sampling_cadence_verified": False,
            "independent_labeller_recoverability_verified": False,
            "empirical_evidence_eligible": False,
            "human_human_agreement_created": False,
            "participant_disjoint_model_validation_created": False,
            "cross_dataset_performance_created": False,
            "gp3_validity_created": False,
            "frozen_evidence_performance_claim_created": False,
        },
        "claim_limit": (
            "This probe verifies only what two pinned secondary Git repositories expose: "
            "one advertises an external transformed common-format collection, while the "
            "other contains code references to two labeller-style filenames. Neither lead "
            "is an obtained authoritative Gaze-in-the-Wild ProcessData/LabelData copy, "
            "resolves dataset-file rights, recovers independent annotation streams, or "
            "opens an empirical, agreement, model-validation, cross-dataset, or GP3 gate."
        ),
    }
    payload["probe_fingerprint_sha256"] = probe_fingerprint(payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("awesome_root", type=Path)
    parser.add_argument("edit_root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build_probe(args.awesome_root.resolve(), args.edit_root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"probe_fingerprint_sha256": payload["probe_fingerprint_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
