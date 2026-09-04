"""Non-empirical review scaffolds bound to exact candidate source inventories."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError
from .source_candidate import CandidateSourceInventory, validate_candidate_source_inventory

_RECORD_TYPE = "candidate-source-review-scaffold-v1"
_SCIENTIFIC_BOUNDARY = {
    "candidate_copy_only": True,
    "review_scaffold_only": True,
    "authorizes_source_audit": False,
    "authorizes_empirical_evidence": False,
    "empirical_evidence_created": False,
}
_ALLOWED_ROLES = {
    "hollywood2em": {"unresolved", "arff", "exclude"},
    "gaze-in-the-wild": {"unresolved", "label", "process", "exclude"},
}


@dataclass(frozen=True, slots=True)
class CandidateSourceReviewFile:
    """One exact candidate file plus deliberately unresolved scientific review fields."""

    path: str
    sha256: str
    bytes: int
    role: str = "unresolved"
    include_in_audit: bool = False
    participant_id: str | None = None
    trial_id: str | None = None
    labeller_id: int | None = None
    process_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic JSON-compatible review row."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CandidateSourceReviewScaffold:
    """Portable manual-review worksheet tied to one exact candidate copy."""

    root: Path
    dataset_key: str
    candidate_inventory_fingerprint_sha256: str
    candidate_file_count: int
    source_review: Mapping[str, Any]
    files: tuple[CandidateSourceReviewFile, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return the portable review-scaffold payload."""
        return {
            "record_type": _RECORD_TYPE,
            "dataset_key": self.dataset_key,
            "candidate_inventory_fingerprint_sha256": (
                self.candidate_inventory_fingerprint_sha256
            ),
            "candidate_file_count": self.candidate_file_count,
            "source_review": dict(self.source_review),
            "files": [row.to_dict() for row in self.files],
            "scientific_boundary": dict(_SCIENTIFIC_BOUNDARY),
        }


def _blank_source_review(dataset_key: str) -> dict[str, Any]:
    common = {
        "dataset_status": "template",
        "dataset_version": "REVIEW_REQUIRED",
        "authoritative_source": "REVIEW_REQUIRED",
        "source_revision": "REVIEW_REQUIRED",
        "license_or_terms": "REVIEW_REQUIRED",
        "reuse_terms_source": "REVIEW_REQUIRED",
        "source_authority_evidence": "REVIEW_REQUIRED",
        "analysis_use_evidence": "REVIEW_REQUIRED",
        "redistribution_evidence": "REVIEW_REQUIRED",
        "coordinate_unit": "unverified",
        "coordinate_verification_basis": "REVIEW_REQUIRED",
        "participant_mapping_basis": "REVIEW_REQUIRED",
        "notes": [],
    }
    if dataset_key == "hollywood2em":
        common.update(
            {
                "annotation_columns_review": "REVIEW_REQUIRED",
                "sampling_rate_review": "REVIEW_REQUIRED",
            }
        )
    else:
        common.update(
            {
                "label_process_mapping_basis": "REVIEW_REQUIRED",
                "labeller_mapping_basis": "REVIEW_REQUIRED",
                "timestamp_sampling_basis": "REVIEW_REQUIRED",
            }
        )
    return common


def build_candidate_source_review_scaffold(
    inventory: CandidateSourceInventory,
) -> CandidateSourceReviewScaffold:
    """Create an unresolved review worksheet from one exact candidate inventory.

    Paths, SHA-256 digests, and byte sizes are copied exactly. No file role, participant, trial,
    labeller, source-authority, licensing, coordinate, or empirical interpretation is inferred.
    """
    if not isinstance(inventory, CandidateSourceInventory):
        raise TypeError("inventory must be a CandidateSourceInventory instance.")
    if inventory.dataset_key not in _ALLOWED_ROLES:
        raise ValueError("Unsupported candidate dataset key.")

    rows = tuple(
        CandidateSourceReviewFile(
            path=item.path,
            sha256=item.sha256,
            bytes=item.bytes,
        )
        for item in inventory.files
    )
    return CandidateSourceReviewScaffold(
        root=inventory.root,
        dataset_key=inventory.dataset_key,
        candidate_inventory_fingerprint_sha256=inventory.inventory_fingerprint_sha256,
        candidate_file_count=inventory.file_count,
        source_review=_blank_source_review(inventory.dataset_key),
        files=rows,
    )


def write_candidate_source_review_scaffold(
    scaffold: CandidateSourceReviewScaffold,
    path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Write a review scaffold outside the candidate tree it describes."""
    if not isinstance(scaffold, CandidateSourceReviewScaffold):
        raise TypeError("scaffold must be a CandidateSourceReviewScaffold instance.")
    target = Path(path)
    resolved_target = target.resolve(strict=False)
    if resolved_target == scaffold.root or scaffold.root in resolved_target.parents:
        raise BenchmarkIntegrityError(
            "Candidate source review output must be outside the candidate source tree so review "
            "metadata cannot mutate the snapshot it describes."
        )
    if target.exists() and not overwrite:
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(scaffold.to_dict(), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return target


def _load_payload(path: Path) -> Mapping[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(
            "Candidate source review scaffold must be valid UTF-8 JSON."
        ) from exc
    if not isinstance(payload, Mapping):
        raise BenchmarkIntegrityError(
            "Candidate source review scaffold must contain one JSON object."
        )
    return payload


def _review_file_from_payload(
    item: Mapping[str, Any],
    *,
    dataset_key: str,
) -> CandidateSourceReviewFile:
    try:
        role = str(item["role"]).strip().lower()
        if role not in _ALLOWED_ROLES[dataset_key]:
            raise BenchmarkIntegrityError(
                f"Unsupported review role {role!r} for {dataset_key}."
            )
        include = item["include_in_audit"]
        if not isinstance(include, bool):
            raise BenchmarkIntegrityError("include_in_audit must be boolean.")
        labeller = item.get("labeller_id")
        if labeller is not None:
            if isinstance(labeller, bool):
                raise BenchmarkIntegrityError("labeller_id must be a positive integer or null.")
            labeller = int(labeller)
            if labeller <= 0:
                raise BenchmarkIntegrityError("labeller_id must be a positive integer or null.")
        return CandidateSourceReviewFile(
            path=str(item["path"]),
            sha256=str(item["sha256"]),
            bytes=int(item["bytes"]),
            role=role,
            include_in_audit=include,
            participant_id=(
                None if item.get("participant_id") is None else str(item["participant_id"])
            ),
            trial_id=None if item.get("trial_id") is None else str(item["trial_id"]),
            labeller_id=labeller,
            process_path=(
                None if item.get("process_path") is None else str(item["process_path"])
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise BenchmarkIntegrityError("Candidate source review file row is invalid.") from exc


def validate_candidate_source_review_scaffold(
    review_path: str | Path,
    inventory_path: str | Path,
    root: str | Path,
) -> CandidateSourceReviewScaffold:
    """Revalidate one manually editable review scaffold against the exact candidate copy.

    Scientific review fields may be edited, but exact file path/hash/size identity and the
    non-empirical scientific boundary cannot change. The scaffold never becomes an audit approval.
    """
    inventory = validate_candidate_source_inventory(inventory_path, root)
    payload = _load_payload(Path(review_path))
    if payload.get("record_type") != _RECORD_TYPE:
        raise BenchmarkIntegrityError(
            f"Candidate source review record_type must be {_RECORD_TYPE!r}."
        )
    if payload.get("dataset_key") != inventory.dataset_key:
        raise BenchmarkIntegrityError("Candidate source review dataset identity does not match.")
    if payload.get("scientific_boundary") != _SCIENTIFIC_BOUNDARY:
        raise BenchmarkIntegrityError(
            "Candidate source review scientific_boundary must preserve non-empirical limits."
        )
    if payload.get("candidate_inventory_fingerprint_sha256") != (
        inventory.inventory_fingerprint_sha256
    ):
        raise BenchmarkIntegrityError(
            "Candidate source review is not bound to the current candidate inventory fingerprint."
        )
    if payload.get("candidate_file_count") != inventory.file_count:
        raise BenchmarkIntegrityError("Candidate source review file count does not match inventory.")

    source_review = payload.get("source_review")
    if not isinstance(source_review, Mapping):
        raise BenchmarkIntegrityError("Candidate source review requires a source_review object.")
    if source_review.get("dataset_status") != "template":
        raise BenchmarkIntegrityError(
            "Candidate source review dataset_status must remain 'template'; this scaffold cannot "
            "authorize empirical use."
        )

    raw_files = payload.get("files")
    if not isinstance(raw_files, list) or len(raw_files) != inventory.file_count:
        raise BenchmarkIntegrityError(
            "Candidate source review must contain exactly one row per inventoried file."
        )
    if not all(isinstance(item, Mapping) for item in raw_files):
        raise BenchmarkIntegrityError("Candidate source review file rows must be JSON objects.")
    rows = tuple(
        _review_file_from_payload(item, dataset_key=inventory.dataset_key) for item in raw_files
    )

    exact_review_identity = [(row.path, row.sha256, row.bytes) for row in rows]
    exact_inventory_identity = [(item.path, item.sha256, item.bytes) for item in inventory.files]
    if exact_review_identity != exact_inventory_identity:
        raise BenchmarkIntegrityError(
            "Candidate source review file path/hash/size identity must exactly match the inventory."
        )

    return CandidateSourceReviewScaffold(
        root=inventory.root,
        dataset_key=inventory.dataset_key,
        candidate_inventory_fingerprint_sha256=inventory.inventory_fingerprint_sha256,
        candidate_file_count=inventory.file_count,
        source_review=dict(source_review),
        files=rows,
    )
