"""Eligibility gate for protocol- and authority-bound VISUS Frozen Evidence review."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .benchmarks import benchmark_fingerprint
from .exceptions import BenchmarkIntegrityError
from .visus_authority_binding import AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD
from .visus_authority_execution_strict import validate_visus_authority_execution_provenance
from .visus_suite import validate_visus_dynamic_aoi_suite_manifest

_SUITE_MANIFEST_NAME = "visus-dynamic-aoi-suite-manifest.json"
_EXECUTION_MANIFEST_NAME = "visus-execution-provenance.json"
_TRANSITION_MANIFEST_NAME = "visus-protocol-authority-transition.json"
_PROTOCOL_VALIDATION_BINDING_NAME = "visus-protocol-bound-validation.json"
_TRANSITION_SCHEMA = "gazeforge-visus-protocol-authority-transition-v1"
_BINDING_SCHEMA = "gazeforge-visus-protocol-bound-validation-v1"
_SOURCE_KEYS = (
    "source_audit_report_fingerprint_sha256",
    "source_audit_spec_fingerprint_sha256",
    "source_manifest_fingerprint_sha256",
    AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD,
)
_PRE_AUTHORITY_SOURCE_KEYS = _SOURCE_KEYS[:3]
_TRANSITION_FALSE_FIELDS = (
    "empirical_validation_authorized_by_transition",
    "empirical_performance_claim_created",
    "formal_preregistration_verified",
    "frozen_evidence_created",
    "raw_source_redistribution_action_authorized",
)
_BINDING_FALSE_FIELDS = (
    "formal_preregistration_verified",
    "empirical_performance_claim_created",
    "dataset_source_authority_promoted",
    "dataset_rights_promoted",
    "frozen_evidence_created",
)


@dataclass(frozen=True, slots=True)
class VisusFrozenEvidenceBundle:
    """Protocol-bound suite and strict execution identities eligible for evidence review."""

    root: Path
    suite_manifest_path: Path
    execution_manifest_path: Path
    transition_manifest_path: Path
    protocol_validation_binding_path: Path
    suite_fingerprint_sha256: str
    execution_fingerprint_sha256: str
    transition_fingerprint_sha256: str
    protocol_validation_binding_fingerprint_sha256: str
    protocol_fingerprint_sha256: str
    protocol_batch_fingerprint_sha256: str
    report_count: int
    source_manifest_fingerprint_sha256: str
    source_authority_certificate_fingerprint_sha256: str


def _valid_sha256(value: Any) -> bool:
    text = str(value).strip().lower()
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text)


def _bundle_root(path: str | Path) -> Path:
    source = Path(path)
    if source.is_dir():
        return source
    if source.name in {
        _SUITE_MANIFEST_NAME,
        _EXECUTION_MANIFEST_NAME,
        _TRANSITION_MANIFEST_NAME,
    }:
        return source.parent
    raise ValueError(
        "VISUS Frozen Evidence path must be a suite directory or one of its bundle manifest files."
    )


def _read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise BenchmarkIntegrityError(f"{label} must be a non-symlink regular file.")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(f"{label} must be valid UTF-8 JSON.") from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(f"{label} must contain one JSON object.")
    return payload


def _file_sha256(path: Path, *, label: str) -> str:
    if path.is_symlink() or not path.is_file():
        raise BenchmarkIntegrityError(f"{label} must be a non-symlink regular file.")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _revalidate_fingerprint(
    record: Mapping[str, Any],
    field: str,
    *,
    label: str,
) -> str:
    claimed = str(record.get(field, ""))
    body = {key: value for key, value in record.items() if key != field}
    if not _valid_sha256(claimed) or benchmark_fingerprint(body) != claimed:
        raise BenchmarkIntegrityError(f"{label} fingerprint does not revalidate.")
    return claimed


def _safe_child(root: Path, relative: str) -> Path:
    if not relative or Path(relative).is_absolute():
        raise BenchmarkIntegrityError("VISUS Frozen Evidence child path is invalid.")
    target = (root / relative).resolve(strict=False)
    resolved_root = root.resolve(strict=False)
    if target == resolved_root or resolved_root not in target.parents:
        raise BenchmarkIntegrityError("VISUS Frozen Evidence child path escapes the suite root.")
    return target


def _transition_summary(
    root: Path,
    suite_path: Path,
    suite: Mapping[str, Any],
) -> tuple[dict[str, Any], str]:
    transition_path = root / _TRANSITION_MANIFEST_NAME
    if not transition_path.is_file():
        raise BenchmarkIntegrityError(
            "VISUS Frozen Evidence bundle is missing the protocol-authority transition seal."
        )
    transition = _read_json_object(
        transition_path,
        label="VISUS protocol-authority transition",
    )
    if transition.get("schema") != _TRANSITION_SCHEMA:
        raise BenchmarkIntegrityError("VISUS protocol-authority transition schema is invalid.")
    if transition.get("status") != "verified-protocol-authority-transition":
        raise BenchmarkIntegrityError("VISUS protocol-authority transition status is invalid.")
    transition_fingerprint = _revalidate_fingerprint(
        transition,
        "transition_fingerprint_sha256",
        label="VISUS protocol-authority transition",
    )

    semantics = transition.get("transition_semantics")
    required_semantics = (
        "original_protocol_validation_preserved",
        "authority_binding_applied_to_isolated_suite_clone",
        "only_suite_manifest_authority_fields_added",
        "child_report_bytes_unchanged",
        "authority_execution_provenance_required_separately",
    )
    if not isinstance(semantics, Mapping) or any(
        semantics.get(field) is not True for field in required_semantics
    ):
        raise BenchmarkIntegrityError("VISUS protocol-authority transition semantics are invalid.")
    if transition.get("source_authority_certificate_consumed") is not True:
        raise BenchmarkIntegrityError(
            "VISUS protocol-authority transition did not consume the reviewed certificate."
        )
    for field in _TRANSITION_FALSE_FIELDS:
        if transition.get(field) is not False:
            raise BenchmarkIntegrityError(
                f"VISUS protocol-authority transition cannot promote {field}."
            )

    suite_fingerprint = str(suite.get("suite_fingerprint_sha256", ""))
    post = transition.get("post_authority_suite")
    pre = transition.get("pre_authority_suite")
    if not isinstance(post, Mapping) or not isinstance(pre, Mapping):
        raise BenchmarkIntegrityError(
            "VISUS protocol-authority transition suite identities are incomplete."
        )
    if post.get("manifest_filename") != suite_path.name:
        raise BenchmarkIntegrityError(
            "VISUS protocol-authority transition names a different authority suite manifest."
        )
    if post.get("suite_fingerprint_sha256") != suite_fingerprint:
        raise BenchmarkIntegrityError(
            "VISUS protocol-authority transition/suite fingerprints disagree."
        )
    if int(post.get("report_count", -1)) != int(suite.get("report_count", -2)):
        raise BenchmarkIntegrityError(
            "VISUS protocol-authority transition/suite report counts disagree."
        )
    if post.get("manifest_sha256") != _file_sha256(
        suite_path,
        label="VISUS authority-bound suite manifest",
    ):
        raise BenchmarkIntegrityError(
            "VISUS protocol-authority transition suite-manifest bytes drifted."
        )
    pre_fingerprint = str(pre.get("suite_fingerprint_sha256", ""))
    if not _valid_sha256(pre_fingerprint):
        raise BenchmarkIntegrityError(
            "VISUS protocol-authority transition pre-authority suite identity is invalid."
        )
    if transition.get("pre_authority_projection_fingerprint_sha256") != pre_fingerprint:
        raise BenchmarkIntegrityError(
            "VISUS protocol-authority transition no longer reconstructs its pre-authority suite."
        )
    if pre_fingerprint == suite_fingerprint:
        raise BenchmarkIntegrityError(
            "VISUS protocol-authority transition did not create a distinct authority suite."
        )

    transition_source = transition.get("source")
    suite_source = suite.get("source")
    if not isinstance(transition_source, Mapping) or not isinstance(suite_source, Mapping):
        raise BenchmarkIntegrityError(
            "VISUS protocol-authority transition/source identity is invalid."
        )
    for key in _SOURCE_KEYS:
        if transition_source.get(key) != suite_source.get(key):
            raise BenchmarkIntegrityError(
                "VISUS protocol-authority transition/suite source identities disagree."
            )

    suite_reports = suite.get("reports")
    child_rows = transition.get("child_reports")
    if not isinstance(suite_reports, list) or not isinstance(child_rows, list):
        raise BenchmarkIntegrityError(
            "VISUS protocol-authority transition child-report ledger is invalid."
        )
    suite_by_name = {
        str(record.get("name", "")): record
        for record in suite_reports
        if isinstance(record, Mapping)
    }
    child_by_name = {
        str(record.get("name", "")): record
        for record in child_rows
        if isinstance(record, Mapping)
    }
    if set(suite_by_name) != set(child_by_name) or len(suite_by_name) != len(suite_reports):
        raise BenchmarkIntegrityError(
            "VISUS protocol-authority transition child-report inventory disagrees with the suite."
        )
    for name, suite_record in suite_by_name.items():
        child = child_by_name[name]
        relative = str(suite_record.get("path", ""))
        child_path = _safe_child(root, relative)
        if child.get("filename") != child_path.name:
            raise BenchmarkIntegrityError(
                "VISUS protocol-authority transition changed a child-report filename."
            )
        if child.get("report_fingerprint_sha256") != suite_record.get(
            "report_fingerprint_sha256"
        ):
            raise BenchmarkIntegrityError(
                "VISUS protocol-authority transition child-report fingerprint drifted."
            )
        if child.get("sha256") != _file_sha256(
            child_path,
            label=f"VISUS authority suite child {name!r}",
        ):
            raise BenchmarkIntegrityError(
                "VISUS protocol-authority transition child-report bytes drifted."
            )
    return transition, transition_fingerprint


def _find_protocol_binding(
    root: Path,
    transition: Mapping[str, Any],
    explicit_path: str | Path | None,
) -> Path:
    filename = str(transition.get("protocol_validation_binding_filename", ""))
    expected_sha = str(transition.get("protocol_validation_binding_file_sha256", ""))
    if filename != _PROTOCOL_VALIDATION_BINDING_NAME or not _valid_sha256(expected_sha):
        raise BenchmarkIntegrityError(
            "VISUS protocol-authority transition protocol-validation binding identity is invalid."
        )
    if explicit_path is not None:
        candidate = Path(explicit_path)
        if candidate.name != filename:
            raise BenchmarkIntegrityError(
                "VISUS Frozen Evidence protocol-validation binding filename is invalid."
            )
        if _file_sha256(candidate, label="VISUS protocol-validation binding") != expected_sha:
            raise BenchmarkIntegrityError(
                "VISUS Frozen Evidence protocol-validation binding bytes disagree with transition."
            )
        return candidate

    search_root = root.parent
    matches: list[Path] = []
    for candidate in search_root.rglob(filename):
        if candidate.is_symlink() or not candidate.is_file():
            continue
        if _file_sha256(candidate, label="VISUS protocol-validation binding") == expected_sha:
            matches.append(candidate)
    if not matches:
        raise BenchmarkIntegrityError(
            "VISUS Frozen Evidence bundle cannot locate the exact protocol-validation binding "
            "recorded by the authority transition."
        )
    if len(matches) != 1:
        raise BenchmarkIntegrityError(
            "VISUS Frozen Evidence protocol-validation binding lookup is ambiguous; supply "
            "protocol_validation_binding_path explicitly."
        )
    return matches[0]


def _validate_protocol_binding(
    path: Path,
    transition: Mapping[str, Any],
    suite: Mapping[str, Any],
) -> tuple[dict[str, Any], str]:
    binding = _read_json_object(path, label="VISUS protocol-validation binding")
    if binding.get("schema") != _BINDING_SCHEMA:
        raise BenchmarkIntegrityError("VISUS protocol-validation binding schema is invalid.")
    if binding.get("status") != "verified-protocol-bound-validation":
        raise BenchmarkIntegrityError("VISUS protocol-validation binding status is invalid.")
    binding_fingerprint = _revalidate_fingerprint(
        binding,
        "binding_fingerprint_sha256",
        label="VISUS protocol-validation binding",
    )
    if transition.get("protocol_validation_binding_fingerprint_sha256") != binding_fingerprint:
        raise BenchmarkIntegrityError(
            "VISUS protocol-validation binding fingerprint disagrees with authority transition."
        )
    if binding.get("protocol_fingerprint_sha256") != transition.get(
        "protocol_fingerprint_sha256"
    ):
        raise BenchmarkIntegrityError(
            "VISUS pre-execution protocol fingerprint disagrees with authority transition."
        )
    if binding.get("protocol_batch_fingerprint_sha256") != transition.get(
        "protocol_batch_fingerprint_sha256"
    ):
        raise BenchmarkIntegrityError(
            "VISUS protocol-batch fingerprint disagrees with authority transition."
        )

    pre = transition.get("pre_authority_suite")
    if not isinstance(pre, Mapping):
        raise BenchmarkIntegrityError(
            "VISUS protocol-authority transition pre-authority suite identity is invalid."
        )
    if binding.get("validation_suite_fingerprint_sha256") != pre.get(
        "suite_fingerprint_sha256"
    ):
        raise BenchmarkIntegrityError(
            "VISUS protocol-validation binding does not identify the transition's pre-authority "
            "suite."
        )

    source = binding.get("source")
    suite_source = suite.get("source")
    if not isinstance(source, Mapping) or not isinstance(suite_source, Mapping):
        raise BenchmarkIntegrityError("VISUS protocol-validation source identity is invalid.")
    for key in _PRE_AUTHORITY_SOURCE_KEYS:
        if source.get(key) != suite_source.get(key):
            raise BenchmarkIntegrityError(
                "VISUS protocol-validation/source authority identities disagree."
            )

    frozen = binding.get("frozen_evaluation")
    if not isinstance(frozen, Mapping) or frozen.get("prediction_emission_grid_used") is not False:
        raise BenchmarkIntegrityError(
            "VISUS protocol-validation binding lost the external evaluation-grid boundary."
        )
    if binding.get("model_human_validation_executed") is not True:
        raise BenchmarkIntegrityError(
            "VISUS protocol-validation binding does not prove model-human execution."
        )
    if binding.get("source_authority_certificate_required_separately") is not True:
        raise BenchmarkIntegrityError(
            "VISUS protocol-validation binding bypasses the separate authority gate."
        )
    if binding.get("source_authority_certificate_bound_by_this_layer") is not False:
        raise BenchmarkIntegrityError(
            "VISUS protocol-validation binding improperly self-certifies source authority."
        )
    for field in _BINDING_FALSE_FIELDS:
        if binding.get(field) is not False:
            raise BenchmarkIntegrityError(
                f"VISUS protocol-validation binding cannot promote {field}."
            )
    return binding, binding_fingerprint


def validate_visus_frozen_evidence_bundle(
    path: str | Path,
    *,
    protocol_validation_binding_path: str | Path | None = None,
) -> dict[str, Any]:
    """Require protocol lineage, authority transition, and strict five-input execution provenance.

    This is a publication-review eligibility integrity gate, not an independent scientific validity
    decision. A v3 bundle must prove the frozen pre-execution protocol -> protocol-bound prediction
    batch -> protocol-bound model-human validation -> isolated authority transition -> strict
    five-input execution chain. Legacy v2 suite/execution pairs deliberately fail closed.
    """
    root = _bundle_root(path)
    suite_path = root / _SUITE_MANIFEST_NAME
    execution_path = root / _EXECUTION_MANIFEST_NAME
    if not suite_path.is_file():
        raise BenchmarkIntegrityError(
            "VISUS Frozen Evidence bundle is missing the validation-suite completion manifest."
        )
    if not execution_path.is_file():
        raise BenchmarkIntegrityError(
            "VISUS Frozen Evidence bundle is missing raw-execution provenance."
        )

    suite = validate_visus_dynamic_aoi_suite_manifest(suite_path, verify_reports=True)
    execution = validate_visus_authority_execution_provenance(
        execution_path,
        verify_suite=True,
    )
    transition, transition_fingerprint = _transition_summary(root, suite_path, suite)
    binding_path = _find_protocol_binding(
        root,
        transition,
        protocol_validation_binding_path,
    )
    binding, binding_fingerprint = _validate_protocol_binding(
        binding_path,
        transition,
        suite,
    )

    suite_fingerprint = str(suite.get("suite_fingerprint_sha256", ""))
    if execution.get("suite_fingerprint_sha256") != suite_fingerprint:
        raise BenchmarkIntegrityError(
            "VISUS Frozen Evidence suite and execution-provenance fingerprints disagree."
        )
    report_count = int(suite.get("report_count", -1))
    if int(execution.get("input_count", -1)) != 5:
        raise BenchmarkIntegrityError(
            "VISUS Frozen Evidence execution provenance must bind exactly five raw inputs."
        )

    source = suite.get("source")
    protocol = suite.get("protocol")
    if not isinstance(source, dict) or not isinstance(protocol, dict):
        raise BenchmarkIntegrityError(
            "VISUS Frozen Evidence suite source/protocol identity is invalid."
        )
    source_identity = {key: str(source.get(key, "")) for key in _SOURCE_KEYS}
    if any(not _valid_sha256(value) for value in source_identity.values()):
        raise BenchmarkIntegrityError(
            "VISUS Frozen Evidence suite source fingerprints are incomplete."
        )
    authority_fingerprint = source_identity[AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD]
    if protocol.get("source_authority_certificate_bound") is not True:
        raise BenchmarkIntegrityError(
            "VISUS Frozen Evidence suite is not sealed to a reviewed authority certificate."
        )
    if protocol.get(AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD) != authority_fingerprint:
        raise BenchmarkIntegrityError(
            "VISUS Frozen Evidence suite authority fingerprint is inconsistent."
        )
    if execution.get(AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD) != authority_fingerprint:
        raise BenchmarkIntegrityError(
            "VISUS Frozen Evidence execution/suite authority fingerprints disagree."
        )
    if execution.get("authority_certificate_semantics_verified") is not True:
        raise BenchmarkIntegrityError(
            "VISUS Frozen Evidence execution did not revalidate authority-certificate semantics."
        )

    return {
        "bundle": "visus-frozen-evidence-v3",
        "status": "verified-protocol-authority-bound-bundle",
        "frozen_evidence_eligible_for_scientific_review": True,
        "scientific_review_completed": False,
        "empirical_performance_claim_created": False,
        "formal_preregistration_verified": False,
        "protocol_bound_lineage_verified": True,
        "suite_manifest_path": str(suite_path),
        "execution_manifest_path": str(execution_path),
        "transition_manifest_path": str(root / _TRANSITION_MANIFEST_NAME),
        "protocol_validation_binding_path": str(binding_path),
        "suite_fingerprint_sha256": suite_fingerprint,
        "execution_fingerprint_sha256": str(
            execution.get("execution_fingerprint_sha256", "")
        ),
        "transition_fingerprint_sha256": transition_fingerprint,
        "protocol_validation_binding_fingerprint_sha256": binding_fingerprint,
        "protocol_fingerprint_sha256": str(binding["protocol_fingerprint_sha256"]),
        "protocol_batch_fingerprint_sha256": str(
            binding["protocol_batch_fingerprint_sha256"]
        ),
        "pre_authority_suite_fingerprint_sha256": str(
            transition["pre_authority_suite"]["suite_fingerprint_sha256"]
        ),
        "report_count": report_count,
        "raw_execution_input_count": int(execution["input_count"]),
        "source": source_identity,
        "protocol": protocol,
        "frozen_evaluation": binding["frozen_evaluation"],
        "lineage": {
            "preexecution_protocol_verified": True,
            "protocol_prediction_batch_verified": True,
            "protocol_model_human_validation_verified": True,
            "authority_transition_verified": True,
            "strict_authority_execution_verified": True,
        },
        "claim_limits": [
            "Bundle eligibility is an integrity gate, not independent empirical validation.",
            (
                "The v3 gate proves artifact lineage through the frozen pre-execution protocol; "
                "it does not make the resulting detector metrics scientifically adequate."
            ),
            (
                "The authority certificate establishes reviewed source identity and "
                "analysis-rights scope; it does not establish participant/stimulus mapping or "
                "scientific validity."
            ),
            "A human reference stream is not ground truth.",
            (
                "Human-human agreement remains unavailable unless separately recoverable "
                "independent streams are verified."
            ),
            "Detector emission frames cannot define the evaluation timestamp grid.",
            (
                "A reviewed redistribution classification does not itself authorize a raw-source "
                "redistribution action."
            ),
            "Passing this gate does not constitute formal preregistration or completed review.",
        ],
    }


def load_visus_frozen_evidence_bundle(
    path: str | Path,
    *,
    protocol_validation_binding_path: str | Path | None = None,
) -> VisusFrozenEvidenceBundle:
    """Return a compact typed record after full protocol- and authority-bound validation."""
    summary = validate_visus_frozen_evidence_bundle(
        path,
        protocol_validation_binding_path=protocol_validation_binding_path,
    )
    root = _bundle_root(path)
    return VisusFrozenEvidenceBundle(
        root=root,
        suite_manifest_path=root / _SUITE_MANIFEST_NAME,
        execution_manifest_path=root / _EXECUTION_MANIFEST_NAME,
        transition_manifest_path=root / _TRANSITION_MANIFEST_NAME,
        protocol_validation_binding_path=Path(summary["protocol_validation_binding_path"]),
        suite_fingerprint_sha256=str(summary["suite_fingerprint_sha256"]),
        execution_fingerprint_sha256=str(summary["execution_fingerprint_sha256"]),
        transition_fingerprint_sha256=str(summary["transition_fingerprint_sha256"]),
        protocol_validation_binding_fingerprint_sha256=str(
            summary["protocol_validation_binding_fingerprint_sha256"]
        ),
        protocol_fingerprint_sha256=str(summary["protocol_fingerprint_sha256"]),
        protocol_batch_fingerprint_sha256=str(summary["protocol_batch_fingerprint_sha256"]),
        report_count=int(summary["report_count"]),
        source_manifest_fingerprint_sha256=str(
            summary["source"]["source_manifest_fingerprint_sha256"]
        ),
        source_authority_certificate_fingerprint_sha256=str(
            summary["source"][AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD]
        ),
    )
