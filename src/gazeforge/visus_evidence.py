"""Eligibility gate for publishing audited VISUS suites as Frozen Evidence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError
from .visus_execution import validate_visus_execution_provenance
from .visus_suite import validate_visus_dynamic_aoi_suite_manifest

_SUITE_MANIFEST_NAME = "visus-dynamic-aoi-suite-manifest.json"
_EXECUTION_MANIFEST_NAME = "visus-execution-provenance.json"
_SOURCE_KEYS = (
    "source_audit_report_fingerprint_sha256",
    "source_audit_spec_fingerprint_sha256",
    "source_manifest_fingerprint_sha256",
)


@dataclass(frozen=True, slots=True)
class VisusFrozenEvidenceBundle:
    """Verified suite plus execution-provenance identities eligible for evidence review."""

    root: Path
    suite_manifest_path: Path
    execution_manifest_path: Path
    suite_fingerprint_sha256: str
    execution_fingerprint_sha256: str
    report_count: int
    source_manifest_fingerprint_sha256: str


def _bundle_root(path: str | Path) -> Path:
    source = Path(path)
    if source.is_dir():
        return source
    if source.name in {_SUITE_MANIFEST_NAME, _EXECUTION_MANIFEST_NAME}:
        return source.parent
    raise ValueError(
        "VISUS Frozen Evidence path must be a suite directory or one of its two manifest files."
    )


def validate_visus_frozen_evidence_bundle(path: str | Path) -> dict[str, Any]:
    """Require both the verified VISUS suite and its raw-execution provenance manifest.

    This is a publication-eligibility integrity gate, not a scientific validity decision. It
    refuses a suite that cannot be tied to the execution-provenance layer introduced for the exact
    reviewed source-audit JSON, human AOI table, model prediction table, and external timestamp-grid
    JSON. It does not establish that the underlying source is authoritative or that its reuse terms
    are correct; those remain source-audit evidence decisions.
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
    execution = validate_visus_execution_provenance(execution_path, verify_suite=True)

    suite_fingerprint = str(suite.get("suite_fingerprint_sha256", ""))
    if execution.get("suite_fingerprint_sha256") != suite_fingerprint:
        raise BenchmarkIntegrityError(
            "VISUS Frozen Evidence suite and execution-provenance fingerprints disagree."
        )
    report_count = int(suite.get("report_count", -1))
    if int(execution.get("input_count", -1)) != 4:
        raise BenchmarkIntegrityError(
            "VISUS Frozen Evidence execution provenance must bind exactly four raw inputs."
        )

    source = suite.get("source")
    if not isinstance(source, dict):
        raise BenchmarkIntegrityError("VISUS Frozen Evidence suite source identity is invalid.")
    source_identity = {key: str(source.get(key, "")) for key in _SOURCE_KEYS}
    if any(len(value) != 64 for value in source_identity.values()):
        raise BenchmarkIntegrityError(
            "VISUS Frozen Evidence suite source fingerprints are incomplete."
        )

    return {
        "bundle": "visus-frozen-evidence-v1",
        "status": "verified-bundle",
        "frozen_evidence_eligible_for_scientific_review": True,
        "suite_manifest_path": str(suite_path),
        "execution_manifest_path": str(execution_path),
        "suite_fingerprint_sha256": suite_fingerprint,
        "execution_fingerprint_sha256": str(
            execution.get("execution_fingerprint_sha256", "")
        ),
        "report_count": report_count,
        "raw_execution_input_count": int(execution["input_count"]),
        "source": source_identity,
        "protocol": suite.get("protocol"),
        "claim_limits": [
            "Bundle eligibility is an integrity gate, not independent empirical validation.",
            "Authoritative-source and reuse-term decisions remain part of the source audit.",
            "A human reference stream is not ground truth.",
            (
                "Human-human agreement remains unavailable unless separately recoverable "
                "independent streams are verified."
            ),
            "Detector emission frames cannot define the evaluation timestamp grid.",
        ],
    }


def load_visus_frozen_evidence_bundle(path: str | Path) -> VisusFrozenEvidenceBundle:
    """Return a compact typed record after full bundle validation."""
    summary = validate_visus_frozen_evidence_bundle(path)
    root = _bundle_root(path)
    return VisusFrozenEvidenceBundle(
        root=root,
        suite_manifest_path=root / _SUITE_MANIFEST_NAME,
        execution_manifest_path=root / _EXECUTION_MANIFEST_NAME,
        suite_fingerprint_sha256=str(summary["suite_fingerprint_sha256"]),
        execution_fingerprint_sha256=str(summary["execution_fingerprint_sha256"]),
        report_count=int(summary["report_count"]),
        source_manifest_fingerprint_sha256=str(
            summary["source"]["source_manifest_fingerprint_sha256"]
        ),
    )
