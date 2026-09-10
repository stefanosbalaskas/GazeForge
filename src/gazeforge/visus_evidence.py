"""Eligibility gate for publishing authority-bound VISUS suites as Frozen Evidence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError
from .visus_authority_binding import AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD
from .visus_authority_execution_strict import validate_visus_authority_execution_provenance
from .visus_suite import validate_visus_dynamic_aoi_suite_manifest

_SUITE_MANIFEST_NAME = "visus-dynamic-aoi-suite-manifest.json"
_EXECUTION_MANIFEST_NAME = "visus-execution-provenance.json"
_SOURCE_KEYS = (
    "source_audit_report_fingerprint_sha256",
    "source_audit_spec_fingerprint_sha256",
    "source_manifest_fingerprint_sha256",
    AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD,
)


@dataclass(frozen=True, slots=True)
class VisusFrozenEvidenceBundle:
    """Verified suite plus authority-bound execution identities eligible for evidence review."""

    root: Path
    suite_manifest_path: Path
    execution_manifest_path: Path
    suite_fingerprint_sha256: str
    execution_fingerprint_sha256: str
    report_count: int
    source_manifest_fingerprint_sha256: str
    source_authority_certificate_fingerprint_sha256: str


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
    """Require the verified suite plus five-input authority-bound execution provenance.

    Frozen Evidence is a publication-eligibility integrity gate, not an independent scientific
    validity decision. Current bundles must bind the reviewed source-authority certificate, exact
    source-audit specification, human AOI table, model prediction table, and external timestamp
    grid. Legacy four-input execution manifests are deliberately ineligible.

    The authority certificate establishes only reviewed source identity and analysis-rights scope.
    Participant/stimulus mappings, coordinates, timestamps, annotation-stream independence, and
    all performance claims remain separate source-audit and validation decisions.
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
    if any(len(value) != 64 for value in source_identity.values()):
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
        "bundle": "visus-frozen-evidence-v2",
        "status": "verified-authority-bound-bundle",
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
        "protocol": protocol,
        "claim_limits": [
            "Bundle eligibility is an integrity gate, not independent empirical validation.",
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
        ],
    }


def load_visus_frozen_evidence_bundle(path: str | Path) -> VisusFrozenEvidenceBundle:
    """Return a compact typed record after full authority-bound bundle validation."""
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
        source_authority_certificate_fingerprint_sha256=str(
            summary["source"][AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD]
        ),
    )
