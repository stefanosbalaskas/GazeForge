from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError

EXPECTED_EVIDENCE_FINGERPRINT = (
    "e16aa3eea5c354ae0c6cb159cb3bdcaede19dfa535fdf23798f9fae3d35154b5"
)
EXPECTED_RECORD_TYPE = (
    "gaze-in-wild-ace-dnv-task-mapping-corroboration-evidence-v1"
)
EXPECTED_REVIEW_STATUS = "secondary_corroboration_only"
EXPECTED_REPOSITORY = "https://github.com/arnejad/ACE-DNV"
EXPECTED_COMMIT = "3142eb4457087743664d96994e952ed784741d1f"
EXPECTED_TREE = "e52618478ba53f945b32f8056df297cf61c85f93"
EXPECTED_DOI = "10.3758/s13428-024-02358-8"

EXPECTED_FILES: dict[str, dict[str, Any]] = {
    "GiW/files_IW&BC.txt": {
        "git_blob_sha1": "02c5cf413530381f8ca4fa1bc206dd753ac59aae",
        "observed_rows": [
            [1, 2, "Ball_Catch"],
            [2, 2, "Ball_Catch"],
            [3, 2, "Ball_Catch"],
            [6, 2, "Ball_Catch"],
            [12, 2, "Ball_Catch"],
            [16, 2, "Ball_Catch"],
            [17, 2, "Ball_Catch"],
            [1, 1, "Indoor_Walk"],
            [2, 1, "Indoor_Walk"],
            [10, 1, "Indoor_Walk"],
            [12, 1, "Indoor_Walk"],
        ],
    },
    "GiW/files_task1_lblr5.txt": {
        "git_blob_sha1": "bda2476b9febc57281dd10e3f1f3a8df54cd8224",
        "observed_rows": [
            [1, 1, "Indoor_Walk"],
            [2, 1, "Indoor_Walk"],
            [17, 1, "Indoor_Walk"],
            [8, 1, "Indoor_Walk"],
            [22, 1, "Indoor_Walk"],
            [18, 1, "Indoor_Walk"],
            [3, 1, "Indoor_Walk"],
            [6, 1, "Indoor_Walk"],
        ],
    },
    "GiW/files_task2_lblr6.txt": {
        "git_blob_sha1": "94f83ad8f770d411edadb6ed15b70be7d386b234",
        "observed_rows": [
            [1, 2, "Ball_Catch"],
            [2, 2, "Ball_Catch"],
            [3, 2, "Ball_Catch"],
            [6, 2, "Ball_Catch"],
            [12, 2, "Ball_Catch"],
            [16, 2, "Ball_Catch"],
            [17, 2, "Ball_Catch"],
        ],
    },
    "GiW/files_tasks3_lblr6.txt": {
        "git_blob_sha1": "3327133c1a8dbb1023014fcf70d3069b54681f14",
        "observed_rows": [
            [8, 3, "Visual_Search"],
            [12, 3, "Visual_Search"],
            [19, 3, "Visual_Search"],
        ],
    },
}

EXPECTED_MAPPINGS = [
    {
        "trial_index": 1,
        "secondary_task_label": "Indoor_Walk",
        "publication_normalized_candidate": "indoor_navigation",
        "participant_ids_observed": [1, 2, 3, 6, 8, 10, 12, 17, 18, 22],
        "supporting_paths": [
            "GiW/files_IW&BC.txt",
            "GiW/files_task1_lblr5.txt",
        ],
    },
    {
        "trial_index": 2,
        "secondary_task_label": "Ball_Catch",
        "publication_normalized_candidate": "ball_catching",
        "participant_ids_observed": [1, 2, 3, 6, 12, 16, 17],
        "supporting_paths": [
            "GiW/files_IW&BC.txt",
            "GiW/files_task2_lblr6.txt",
        ],
    },
    {
        "trial_index": 3,
        "secondary_task_label": "Visual_Search",
        "publication_normalized_candidate": "visual_search",
        "participant_ids_observed": [8, 12, 19],
        "supporting_paths": ["GiW/files_tasks3_lblr6.txt"],
    },
]

EXPECTED_BOUNDARY_KEYS = {
    "authoritative_trial_task_mapping_verified",
    "complete_trial_task_mapping_verified",
    "task_stratified_validation_authorized",
    "task_stratified_validation_created",
    "new_empirical_performance_claim_created",
    "cross_dataset_validation_created",
    "native_60hz_validity_created",
    "gp3_validity_created",
    "acquisition_hardware_cadence_verified",
    "quarantine_exit_authorized",
}


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise BenchmarkIntegrityError(message)


def validate_gaze_in_wild_ace_dnv_task_mapping_evidence(
    record: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the frozen ACE-DNV secondary task-mapping corroboration record.

    The contract is intentionally fail-closed. It can preserve secondary evidence
    that ACE-DNV used GIW TrIdx 1/2/3 for three named tasks, but it cannot promote
    that evidence into a first-party/authoritative mapping or infer TrIdx 4.
    """

    payload = dict(record)
    actual_fingerprint = payload.get("evidence_fingerprint_sha256")
    body = dict(payload)
    body.pop("evidence_fingerprint_sha256", None)
    recomputed_fingerprint = _canonical_sha256(body)

    _require(
        actual_fingerprint == recomputed_fingerprint,
        "ACE-DNV task-mapping evidence fingerprint does not match its body",
    )
    _require(
        actual_fingerprint == EXPECTED_EVIDENCE_FINGERPRINT,
        "ACE-DNV task-mapping evidence fingerprint is not the reviewed identity",
    )
    _require(
        payload.get("record_type") == EXPECTED_RECORD_TYPE,
        "ACE-DNV task-mapping evidence record type drifted",
    )
    _require(
        payload.get("dataset") == "Gaze-in-the-Wild",
        "ACE-DNV task-mapping evidence dataset drifted",
    )
    _require(
        payload.get("review_status") == EXPECTED_REVIEW_STATUS,
        "ACE-DNV task-mapping evidence must remain secondary corroboration only",
    )

    source = payload.get("source")
    _require(isinstance(source, Mapping), "ACE-DNV task-mapping source is missing")
    _require(
        source.get("classification") == "secondary_replication_source",
        "ACE-DNV task-mapping source classification drifted",
    )
    _require(
        source.get("repository") == EXPECTED_REPOSITORY,
        "ACE-DNV task-mapping repository drifted",
    )
    _require(
        source.get("pinned_commit_sha1") == EXPECTED_COMMIT,
        "ACE-DNV task-mapping commit drifted",
    )
    _require(
        source.get("pinned_tree_sha1") == EXPECTED_TREE,
        "ACE-DNV task-mapping tree drifted",
    )

    paper = source.get("paper")
    _require(isinstance(paper, Mapping), "ACE-DNV paper provenance is missing")
    _require(
        paper.get("doi") == EXPECTED_DOI,
        "ACE-DNV paper DOI drifted",
    )
    _require(
        paper.get("published_date") == "2024-03-06",
        "ACE-DNV paper publication date drifted",
    )
    _require(
        paper.get("relationship_to_giw")
        == "secondary_methodological_study_using_gaze_in_the_wild",
        "ACE-DNV relationship-to-GIW classification drifted",
    )

    files = source.get("files")
    _require(isinstance(files, Mapping), "ACE-DNV task-mapping files are missing")
    _require(
        set(files) == set(EXPECTED_FILES),
        "ACE-DNV task-mapping source file inventory drifted",
    )
    for path, expected in EXPECTED_FILES.items():
        _require(
            files[path] == expected,
            f"ACE-DNV task-mapping source identity/content drifted for {path}",
        )

    corroboration = payload.get("secondary_corroboration")
    _require(
        isinstance(corroboration, Mapping),
        "ACE-DNV task-mapping corroboration section is missing",
    )
    _require(
        corroboration.get("trial_mappings") == EXPECTED_MAPPINGS,
        "ACE-DNV partial trial-task corroboration drifted",
    )
    _require(
        corroboration.get("partial_trial_task_corroboration_recorded") is True,
        "ACE-DNV partial corroboration flag must remain true",
    )
    _require(
        corroboration.get("complete_mapping_recorded") is False,
        "ACE-DNV evidence cannot promote a complete task mapping",
    )

    trial4 = corroboration.get("trial_index_4")
    _require(
        trial4
        == {
            "status": "unresolved",
            "explicit_secondary_task_label_found_in_reviewed_ace_dnv_files": False,
            "tea_making_inferred_by_elimination": False,
        },
        "ACE-DNV TrIdx 4 must remain explicitly unresolved",
    )

    boundary = payload.get("scientific_boundary")
    _require(
        isinstance(boundary, Mapping),
        "ACE-DNV scientific boundary is missing",
    )
    _require(
        set(boundary) == EXPECTED_BOUNDARY_KEYS,
        "ACE-DNV scientific boundary contract drifted",
    )
    _require(
        not any(bool(value) for value in boundary.values()),
        "ACE-DNV secondary corroboration cannot promote scientific gates",
    )

    claim_limit = payload.get("claim_limit")
    _require(
        isinstance(claim_limit, str)
        and "secondary corroboration" in claim_limit
        and "TrIdx 4 remains unresolved" in claim_limit
        and "Tea_Making is not inferred by elimination" in claim_limit,
        "ACE-DNV claim limit drifted",
    )

    return payload


def load_gaze_in_wild_ace_dnv_task_mapping_evidence(
    path: str | Path,
) -> dict[str, Any]:
    """Load and validate the frozen ACE-DNV secondary corroboration record."""

    record = json.loads(Path(path).read_text(encoding="utf-8"))
    _require(
        isinstance(record, Mapping),
        "ACE-DNV task-mapping evidence must be a JSON object",
    )
    return validate_gaze_in_wild_ace_dnv_task_mapping_evidence(record)
