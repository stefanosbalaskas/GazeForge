"""Validation for frozen Hollywood2EM canonical-GIN history evidence."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError

RECORD_TYPE = "hollywood2-gin-history-evidence-v1"
PROBE_RECORD_TYPE = "hollywood2-gin-history-probe-v1"
STATUS = (
    "verified_complete_reachable_git_history_no_repository_license_or_"
    "participant_mapping_recovered"
)
EXPECTED_EVIDENCE_FINGERPRINT_SHA256 = (
    "c7d2f477a66feca3676482ffdabff2b0778196db99e48b86104fe86d0f5bfae1"
)
GIN_REPOSITORY = "https://gin.g-node.org/ioannis.agtzidis/hollywood2_em.git"
GIN_HEAD = "870fa6d6209c9085260918d61433a0a2c70fd497"
INITIAL_COMMIT = "1e80c3e0c1527fd4fdf6a2bc880a7c43c861eed0"
GROUND_TRUTH_MOVE_COMMIT = "357bafd1decbea23eb2fe7cfd0fa1420c25d955c"
GROUND_TRUTH_PATH_FINGERPRINT = (
    "0a8e49b3ae814bee212176557cc71c0d5658cdcf56d16f1c75b15c0566ee989d"
)
GIN_TOKENS = (
    "001",
    "002",
    "003",
    "004",
    "005",
    "006",
    "008",
    "010",
    "011",
    "012",
    "013",
    "014",
    "015",
    "017",
    "018",
    "019",
)


@dataclass(frozen=True, slots=True)
class Hollywood2GinHistoryEvidence:
    """Compact typed identity for the immutable history evidence record."""

    path: Path | None
    fingerprint_sha256: str
    commit_count: int
    repository_license_file_recovered: bool
    participant_identity_mapping_verified: bool


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def evidence_fingerprint(record: Mapping[str, Any]) -> str:
    """Return the canonical SHA-256 excluding the stored fingerprint field."""

    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _load_mapping(
    record_or_path: Mapping[str, Any] | str | Path,
    *,
    label: str,
) -> tuple[dict[str, Any], Path | None]:
    if isinstance(record_or_path, Mapping):
        return dict(record_or_path), None
    path = Path(record_or_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(f"Could not load {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(f"{label} must contain one JSON object.")
    return payload, path


def _mapping(record: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = record.get(key)
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(f"Hollywood2 history field {key!r} is missing.")
    return value


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BenchmarkIntegrityError(f"Hollywood2 history {label} drifted.")


def _true(value: Any, label: str) -> None:
    if value is not True:
        raise BenchmarkIntegrityError(f"Hollywood2 history must preserve {label}.")


def _false(value: Any, label: str) -> None:
    if value is not False:
        raise BenchmarkIntegrityError(f"Hollywood2 history must not promote {label}.")


def validate_hollywood2_gin_history_evidence(
    record_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Strictly validate the immutable reviewed canonical-GIN history record."""

    record, _ = _load_mapping(record_or_path, label="Hollywood2 GIN history evidence")
    _equal(record.get("record_type"), RECORD_TYPE, "record type")
    _equal(record.get("status"), STATUS, "status")
    _equal(record.get("checked_on"), "2026-09-05", "review date")

    scope = _mapping(record, "scope")
    _equal(scope.get("repository"), GIN_REPOSITORY, "repository")
    _equal(scope.get("pinned_commit_sha1"), GIN_HEAD, "pinned commit")
    _equal(
        scope.get("history_scope"),
        "all commits reachable from the pinned canonical HEAD",
        "history scope",
    )

    repository = _mapping(record, "repository_history")
    _equal(repository.get("commit_count"), 7, "commit count")
    _equal(repository.get("initial_commit_sha1"), INITIAL_COMMIT, "initial commit")
    _equal(repository.get("head_commit_sha1"), GIN_HEAD, "head commit")
    _equal(
        repository.get("initial_commit_subject"),
        "Labelled EM added",
        "initial commit subject",
    )
    _equal(
        repository.get("single_observed_commit_author_name"),
        "Ioannis Agtzidis",
        "single observed author",
    )
    subjects = repository.get("commit_subjects")
    if not isinstance(subjects, list) or len(subjects) != 7:
        raise BenchmarkIntegrityError(
            "Hollywood2 history must preserve all seven reachable commit summaries."
        )

    license_history = _mapping(record, "license_history")
    _true(license_history.get("complete_reachable_history_searched"), "history search")
    _equal(license_history.get("license_named_file_occurrence_count"), 0, "license count")
    _equal(license_history.get("unique_license_blob_count"), 0, "license blob count")
    _equal(license_history.get("readme_unique_version_count"), 3, "README count")
    for key, label in (
        ("license_or_copying_named_file_ever_present", "historical license-file recovery"),
        ("readme_license_or_licence_keyword_ever_present", "README licence wording"),
        ("exact_license_identifier_recovered_from_git_history", "exact license identifier"),
        ("exact_license_text_recovered_from_git_history", "exact license text"),
        (
            "raw_annotation_redistribution_terms_recovered_from_git_history",
            "annotation redistribution terms",
        ),
    ):
        _false(license_history.get(key), label)

    readme = _mapping(record, "readme_history")
    _equal(readme.get("unique_version_count"), 3, "README history count")
    _false(
        readme.get("participant_or_identity_keyword_ever_present"),
        "README participant-identity mapping",
    )
    versions = readme.get("versions")
    if not isinstance(versions, list) or len(versions) != 3:
        raise BenchmarkIntegrityError("Hollywood2 history must preserve three README versions.")
    if any(item.get("keyword_lines") != [] for item in versions if isinstance(item, Mapping)):
        raise BenchmarkIntegrityError(
            "Hollywood2 history README keyword evidence must remain empty."
        )

    ground = _mapping(record, "ground_truth_path_history")
    _equal(ground.get("initial_commit_tree_path_count"), 697, "initial tree count")
    _equal(
        ground.get("initial_commit_ground_truth_directory_file_count"),
        0,
        "initial ground_truth directory count",
    )
    _equal(
        ground.get("ground_truth_directory_first_present_commit_sha1"),
        GROUND_TRUTH_MOVE_COMMIT,
        "ground_truth move commit",
    )
    _equal(ground.get("ground_truth_file_count"), 697, "ground-truth file count")
    _equal(ground.get("clip_count"), 56, "clip count")
    _equal(ground.get("file_subject_token_count"), 16, "token count")
    _equal(tuple(ground.get("file_subject_tokens", [])), GIN_TOKENS, "token inventory")
    _equal(
        ground.get("ground_truth_path_fingerprint_sha256"),
        GROUND_TRUTH_PATH_FINGERPRINT,
        "ground-truth path fingerprint",
    )
    _equal(ground.get("token_set_version_count"), 1, "token-set version count")
    _equal(ground.get("path_inventory_version_count"), 1, "path-inventory version count")
    _true(
        ground.get("all_697_current_ground_truth_paths_first_seen_in_move_commit"),
        "single move-commit first-seen inventory",
    )
    _true(ground.get("filename_schema_match"), "filename schema match")

    context = _mapping(record, "cross_evidence_context")
    _equal(
        context.get("author_open_source_declaration_evidence_fingerprint_sha256"),
        "a08510e43caca2a8e6d5c85e7b1ad41c9f312247cd9bd8367372f8ecad8aacab",
        "annotation-provenance cross-evidence fingerprint",
    )
    _true(
        context.get("author_open_source_declaration_verified_elsewhere"),
        "separate author declaration",
    )
    _true(
        context.get("upstream_unique_subject_id_semantics_verified_elsewhere"),
        "separate upstream unique-ID semantics",
    )
    _false(context.get("history_provides_exact_license_identifier"), "history license claim")
    _false(
        context.get("history_links_filename_tokens_to_original_subject_ids"),
        "history participant mapping claim",
    )

    boundary = _mapping(record, "scientific_boundary")
    _true(boundary.get("complete_reachable_git_history_audited"), "complete history audit")
    _true(
        boundary.get("filename_tokens_stable_from_ground_truth_move_commit"),
        "stable token syntax",
    )
    for key, label in (
        ("historical_repository_license_file_recovered", "historical license-file recovery"),
        ("historical_readme_license_text_recovered", "historical README license text"),
        (
            "exact_annotation_repository_license_identifier_verified",
            "exact annotation-repository license",
        ),
        ("annotation_repository_redistribution_terms_verified", "redistribution terms"),
        (
            "filename_token_to_original_participant_id_mapping_verified",
            "filename-token participant mapping",
        ),
        (
            "participant_group_membership_by_filename_token_verified",
            "participant group mapping",
        ),
        ("participant_identity_mapping_verified", "participant identity mapping"),
        ("participant_disjoint_model_validation_created", "participant-disjoint modelling"),
        ("cross_dataset_validation_created", "cross-dataset validation"),
        ("independent_human_human_agreement_created", "independent human agreement"),
        ("frozen_evidence_performance_claim_created", "Frozen Evidence performance"),
    ):
        _false(boundary.get(key), label)

    limits = record.get("claim_limits")
    actions = record.get("next_required_actions")
    if not isinstance(limits, list) or len(limits) < 4:
        raise BenchmarkIntegrityError("Hollywood2 history must retain explicit claim limits.")
    if not isinstance(actions, list) or len(actions) < 2:
        raise BenchmarkIntegrityError("Hollywood2 history must retain next required actions.")

    stored = str(record.get("evidence_fingerprint_sha256", ""))
    calculated = evidence_fingerprint(record)
    if stored != calculated:
        raise BenchmarkIntegrityError("Hollywood2 history evidence self-fingerprint is invalid.")
    if stored != EXPECTED_EVIDENCE_FINGERPRINT_SHA256:
        raise BenchmarkIntegrityError("Hollywood2 immutable history evidence fingerprint drifted.")
    return record


def validate_hollywood2_gin_history_probe(
    probe_or_path: Mapping[str, Any] | str | Path,
    evidence_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Bind a fresh complete-history probe to the frozen reviewed evidence."""

    probe, _ = _load_mapping(probe_or_path, label="Hollywood2 GIN history probe")
    evidence = validate_hollywood2_gin_history_evidence(evidence_or_path)
    _equal(probe.get("record_type"), PROBE_RECORD_TYPE, "live probe record type")
    _equal(probe.get("repository"), GIN_REPOSITORY, "live probe repository")
    _equal(probe.get("pinned_head_sha1"), GIN_HEAD, "live probe pinned head")
    _equal(probe.get("observed_head_sha1"), GIN_HEAD, "live probe observed head")

    history = _mapping(probe, "history")
    repository = _mapping(evidence, "repository_history")
    _equal(history.get("commit_count"), repository.get("commit_count"), "live commit count")
    _equal(
        history.get("initial_commit_sha1"),
        repository.get("initial_commit_sha1"),
        "live initial commit",
    )
    _equal(history.get("head_commit_sha1"), GIN_HEAD, "live head commit")

    live_license = _mapping(history, "license_history")
    frozen_license = _mapping(evidence, "license_history")
    _equal(
        live_license.get("license_named_file_ever_present"),
        frozen_license.get("license_or_copying_named_file_ever_present"),
        "live license history",
    )
    _equal(
        live_license.get("occurrence_count"),
        frozen_license.get("license_named_file_occurrence_count"),
        "live license occurrences",
    )

    live_readme = _mapping(history, "readme_history")
    frozen_readme = _mapping(evidence, "readme_history")
    _equal(
        live_readme.get("unique_version_count"),
        frozen_readme.get("unique_version_count"),
        "live README version count",
    )
    _equal(
        live_readme.get("license_keyword_ever_present"),
        frozen_license.get("readme_license_or_licence_keyword_ever_present"),
        "live README license search",
    )
    _equal(
        live_readme.get("identity_keyword_ever_present"),
        frozen_readme.get("participant_or_identity_keyword_ever_present"),
        "live README identity search",
    )

    live_ground = _mapping(history, "ground_truth_history")
    frozen_ground = _mapping(evidence, "ground_truth_path_history")
    current = _mapping(live_ground, "current")
    for live_key, frozen_key in (
        ("file_count", "ground_truth_file_count"),
        ("clip_count", "clip_count"),
        ("file_subject_token_count", "file_subject_token_count"),
        ("path_fingerprint_sha256", "ground_truth_path_fingerprint_sha256"),
    ):
        _equal(current.get(live_key), frozen_ground.get(frozen_key), f"live {live_key}")
    _equal(
        tuple(current.get("file_subject_tokens", [])),
        tuple(frozen_ground.get("file_subject_tokens", [])),
        "live token inventory",
    )
    _equal(
        live_ground.get("token_set_version_count"),
        frozen_ground.get("token_set_version_count"),
        "live token-set version count",
    )
    _equal(
        live_ground.get("path_inventory_version_count"),
        frozen_ground.get("path_inventory_version_count"),
        "live path-inventory version count",
    )
    _equal(
        live_ground.get("first_seen_fingerprint_sha256"),
        frozen_ground.get("first_seen_fingerprint_sha256"),
        "live first-seen fingerprint",
    )
    return probe


def load_hollywood2_gin_history_evidence(
    record_or_path: Mapping[str, Any] | str | Path,
) -> Hollywood2GinHistoryEvidence:
    """Return a compact typed identity after strict immutable validation."""

    record, path = _load_mapping(record_or_path, label="Hollywood2 GIN history evidence")
    validated = validate_hollywood2_gin_history_evidence(record)
    repository = _mapping(validated, "repository_history")
    boundary = _mapping(validated, "scientific_boundary")
    return Hollywood2GinHistoryEvidence(
        path=path,
        fingerprint_sha256=str(validated["evidence_fingerprint_sha256"]),
        commit_count=int(repository["commit_count"]),
        repository_license_file_recovered=bool(
            boundary["historical_repository_license_file_recovered"]
        ),
        participant_identity_mapping_verified=bool(
            boundary["participant_identity_mapping_verified"]
        ),
    )
