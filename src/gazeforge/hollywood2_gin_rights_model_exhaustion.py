"""Fail-closed Hollywood2EM GIN rights-model exhaustion evidence.

This layer distinguishes repository accessibility from dataset licensing. It binds
reviewed Hollywood2EM rights evidence to pinned first-party GIN infrastructure
identities without inferring an exact licence, analysis permission, or
redistribution permission.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError
from .hollywood2_author_license_evidence import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256 as AUTHOR_FP,
)
from .hollywood2_author_license_evidence import validate_hollywood2_author_license_evidence
from .hollywood2_copy_rights_roadmap_sync import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256 as ROADMAP_FP,
)
from .hollywood2_copy_rights_roadmap_sync import validate_hollywood2_copy_rights_roadmap_sync
from .hollywood2_gin_accessible_host_evidence import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256 as ACCESS_FP,
)
from .hollywood2_gin_accessible_host_evidence import (
    validate_hollywood2_gin_accessible_host_evidence,
)
from .hollywood2_history_evidence import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256 as HISTORY_FP,
)
from .hollywood2_history_evidence import validate_hollywood2_gin_history_evidence

RECORD_TYPE = "hollywood2-gin-rights-model-exhaustion-evidence-v1"
STATUS = "verified-gin-access-model-is-not-dataset-license-exact-rights-unresolved"
EXPECTED_EVIDENCE_FINGERPRINT_SHA256 = (
    "df642aea3fc076caa42e4a6448694e2b14a58d16aa08d780ee968612ab9728d1"
)
GIN_REPOSITORY = "https://gin.g-node.org/ioannis.agtzidis/hollywood2_em.git"
GIN_COMMIT = "870fa6d6209c9085260918d61433a0a2c70fd497"

GOGS_REPOSITORY = "https://github.com/G-Node/gogs"
GOGS_COMMIT = "966e925cf320beff768b192276774d9265706df5"
GOGS_TREE = "81f945c4e2278ec9d26fae1a48d32e5f9814badb"
GOGS_README_BLOB = "72a83599065aff8bacf6a428bacbdc95e086dc8f"
LIBGIN_REPOSITORY = "https://github.com/G-Node/libgin"
LIBGIN_COMMIT = "50fbb82301a29e62731ee1564bfe43642c936ae4"
LIBGIN_TREE = "2341bc1edafc8c494bb2562e50bad2a08be19b69"
LIBGIN_DOI_BLOB = "d2ac4b28cd29772e1f051c8690e510e1018a1168"

DEFAULT_AUTHOR_PATH = Path(
    "validation/evidence/hollywood2/hollywood2-author-license-statement-evidence-v1.json"
)
DEFAULT_ACCESS_PATH = Path(
    "validation/evidence/hollywood2/hollywood2-gin-host-metadata-accessible-evidence-v1.json"
)
DEFAULT_HISTORY_PATH = Path(
    "validation/evidence/hollywood2/hollywood2-gin-history-evidence-v1.json"
)
DEFAULT_ROADMAP_PATH = Path(
    "validation/evidence/hollywood2/hollywood2-copy-rights-roadmap-sync-evidence-v1.json"
)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def evidence_fingerprint(record: Mapping[str, Any]) -> str:
    """Return the canonical SHA-256 excluding the self-fingerprint field."""
    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _load(record_or_path: Mapping[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(record_or_path, Mapping):
        return dict(record_or_path)
    try:
        payload = json.loads(Path(record_or_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(
            f"Could not load Hollywood2 GIN rights-model evidence: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError("Hollywood2 GIN rights-model evidence must be an object.")
    return payload


def _mapping(record: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = record.get(key)
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(f"Hollywood2 GIN rights-model field {key!r} is missing.")
    return value


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BenchmarkIntegrityError(f"Hollywood2 GIN rights-model {label} drifted.")


def _true(value: Any, label: str) -> None:
    if value is not True:
        raise BenchmarkIntegrityError(f"Hollywood2 GIN rights-model must preserve {label}.")


def _false(value: Any, label: str) -> None:
    if value is not False:
        raise BenchmarkIntegrityError(f"Hollywood2 GIN rights-model must not promote {label}.")


def _validate_infrastructure(record: Mapping[str, Any]) -> None:
    infrastructure = _mapping(record, "gin_first_party_infrastructure_evidence")
    gogs = _mapping(infrastructure, "gogs")
    expected_gogs = {
        "repository": GOGS_REPOSITORY,
        "commit_sha1": GOGS_COMMIT,
        "tree_sha1": GOGS_TREE,
        "readme_blob_sha1": GOGS_README_BLOB,
        "public_repository_access_statement_present": True,
        "software_project_license": "MIT",
        "software_license_applies_to_hollywood2em_data": False,
    }
    for key, expected in expected_gogs.items():
        _equal(gogs.get(key), expected, f"G-Node/gogs {key}")

    libgin = _mapping(infrastructure, "libgin")
    expected_libgin = {
        "repository": LIBGIN_REPOSITORY,
        "commit_sha1": LIBGIN_COMMIT,
        "tree_sha1": LIBGIN_TREE,
        "doi_go_blob_sha1": LIBGIN_DOI_BLOB,
        "repository_yaml_has_optional_license_field": True,
        "license_is_repository_metadata_not_global_service_default": True,
    }
    for key, expected in expected_libgin.items():
        _equal(libgin.get(key), expected, f"G-Node/libgin {key}")


def _validate_rights(record: Mapping[str, Any]) -> None:
    rights = _mapping(record, "rights_model_interpretation")
    _true(
        rights.get("dataset_license_is_modeled_as_repository_specific_metadata"),
        "dataset-specific licence metadata",
    )
    _true(
        rights.get("author_general_open_source_license_indication_verified"),
        "author open-source-licence indication",
    )
    for key, label in (
        ("gin_public_access_is_dataset_license", "public access as a dataset licence"),
        ("gin_software_mit_license_is_dataset_license", "GIN software MIT as dataset licence"),
        (
            "gin_service_assigns_one_automatic_license_to_all_public_datasets",
            "a service-wide automatic dataset licence",
        ),
        ("exact_hollywood2em_license_identifier_recovered", "exact licence identifier"),
        ("exact_hollywood2em_license_text_recovered", "exact licence text"),
        ("analysis_use_authorized", "analysis-use authorization"),
        ("raw_data_redistribution_authorized", "raw-data redistribution authorization"),
        ("rights_roadmap_component_resolved", "rights roadmap resolution"),
    ):
        _false(rights.get(key), label)

    boundary = _mapping(record, "scientific_boundary")
    for key in (
        "participant_identity_mapping_verified",
        "source_audit_ready",
        "participant_disjoint_model_validation_created",
        "cross_dataset_validation_created",
        "independent_human_human_agreement_created",
        "frozen_evidence_performance_claim_created",
        "new_empirical_performance_claim_created",
        "native_60hz_or_gp3_validity_created",
    ):
        _false(boundary.get(key), key)


def validate_hollywood2_gin_rights_model_exhaustion(
    record_or_path: Mapping[str, Any] | str | Path,
    *,
    author_path: str | Path = DEFAULT_AUTHOR_PATH,
    access_path: str | Path = DEFAULT_ACCESS_PATH,
    history_path: str | Path = DEFAULT_HISTORY_PATH,
    roadmap_path: str | Path = DEFAULT_ROADMAP_PATH,
) -> dict[str, Any]:
    """Validate the immutable rights-model exhaustion record and its upstreams."""
    record = _load(record_or_path)
    _equal(record.get("record_type"), RECORD_TYPE, "record type")
    _equal(record.get("status"), STATUS, "status")
    _equal(record.get("checked_on"), "2026-09-09", "review date")

    canonical = _mapping(record, "canonical_repository")
    _equal(canonical.get("repository"), GIN_REPOSITORY, "canonical repository")
    _equal(canonical.get("pinned_commit_sha1"), GIN_COMMIT, "canonical commit")
    _true(canonical.get("canonical_copy_identity_verified"), "canonical copy identity")
    _true(
        canonical.get("public_host_accessibility_verified_elsewhere"),
        "reviewed public-host accessibility",
    )

    upstream = _mapping(record, "reviewed_upstream_evidence")
    expected_upstream = {
        "author_license_statement_evidence_fingerprint_sha256": AUTHOR_FP,
        "gin_accessible_host_evidence_fingerprint_sha256": ACCESS_FP,
        "gin_history_evidence_fingerprint_sha256": HISTORY_FP,
        "copy_rights_roadmap_sync_evidence_fingerprint_sha256": ROADMAP_FP,
    }
    for key, expected in expected_upstream.items():
        _equal(upstream.get(key), expected, f"upstream fingerprint {key}")

    author = validate_hollywood2_author_license_evidence(author_path)
    access = validate_hollywood2_gin_accessible_host_evidence(access_path)
    history = validate_hollywood2_gin_history_evidence(history_path)
    roadmap = validate_hollywood2_copy_rights_roadmap_sync(roadmap_path)
    observed = (
        (author, "author_license_statement_evidence_fingerprint_sha256"),
        (access, "gin_accessible_host_evidence_fingerprint_sha256"),
        (history, "gin_history_evidence_fingerprint_sha256"),
        (roadmap, "copy_rights_roadmap_sync_evidence_fingerprint_sha256"),
    )
    for upstream_record, key in observed:
        _equal(
            upstream_record.get("evidence_fingerprint_sha256"),
            upstream.get(key),
            f"revalidated upstream {key}",
        )

    _validate_infrastructure(record)
    _validate_rights(record)
    limits = record.get("claim_limits")
    if not isinstance(limits, list) or len(limits) != 6:
        raise BenchmarkIntegrityError("Hollywood2 GIN rights-model must retain six claim limits.")
    action = record.get("next_required_action")
    if not isinstance(action, str) or not action.strip():
        raise BenchmarkIntegrityError("Hollywood2 GIN rights-model next action is missing.")

    stored = str(record.get("evidence_fingerprint_sha256", ""))
    _equal(stored, evidence_fingerprint(record), "self-fingerprint")
    _equal(stored, EXPECTED_EVIDENCE_FINGERPRINT_SHA256, "immutable fingerprint")
    return record
