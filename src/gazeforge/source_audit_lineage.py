"""Cryptographic lineage receipts for authorized source-audit reports."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .benchmarks import benchmark_fingerprint
from .exceptions import BenchmarkIntegrityError
from .gaze_in_wild_audit import GazeInWildSourceAuditSpec
from .hollywood2_audit import Hollywood2SourceAuditSpec
from .source_candidate_authorization import (
    CandidateSourceAuditAuthorization,
    authorize_candidate_source_audit_template,
    source_audit_template_fingerprint,
)

AuditTemplateSpec = Hollywood2SourceAuditSpec | GazeInWildSourceAuditSpec

_RECORD_TYPE = "source-audit-lineage-receipt-v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SCIENTIFIC_BOUNDARY = {
    "lineage_receipt_only": True,
    "creates_new_empirical_metrics": False,
    "creates_frozen_evidence": False,
    "promotes_native_gp3_evidence": False,
}


@dataclass(frozen=True, slots=True)
class SourceAuditLineageReceipt:
    """Verified chain from reviewed template through authorization to source-audit report."""

    dataset_key: str
    audit_template_fingerprint_sha256: str
    authorization_fingerprint_sha256: str
    authorized_spec_fingerprint_sha256: str
    audit_report_fingerprint_sha256: str
    source_manifest_fingerprints_sha256: Mapping[str, str]
    source_revision: str
    source_audit_verified: bool = True
    lineage_verified: bool = True

    def __post_init__(self) -> None:
        dataset_key = str(self.dataset_key).strip().lower()
        if dataset_key not in {"hollywood2em", "gaze-in-the-wild"}:
            raise ValueError("Unsupported source-audit lineage dataset key.")
        object.__setattr__(self, "dataset_key", dataset_key)
        for field_name in (
            "audit_template_fingerprint_sha256",
            "authorization_fingerprint_sha256",
            "authorized_spec_fingerprint_sha256",
            "audit_report_fingerprint_sha256",
        ):
            value = str(getattr(self, field_name)).strip().lower()
            if _SHA256_RE.fullmatch(value) is None:
                raise ValueError(f"{field_name} must contain exactly 64 hexadecimal characters.")
            object.__setattr__(self, field_name, value)
        if not isinstance(self.source_audit_verified, bool) or not self.source_audit_verified:
            raise ValueError("source_audit_verified must be true for a lineage receipt.")
        if not isinstance(self.lineage_verified, bool) or not self.lineage_verified:
            raise ValueError("lineage_verified must be true for a lineage receipt.")
        revision = str(self.source_revision).strip()
        if not revision:
            raise ValueError("source_revision must not be empty.")
        object.__setattr__(self, "source_revision", revision)
        fingerprints = dict(self.source_manifest_fingerprints_sha256)
        expected_keys = (
            {"source"} if dataset_key == "hollywood2em" else {"label", "process"}
        )
        if set(fingerprints) != expected_keys:
            raise ValueError(
                "source_manifest_fingerprints_sha256 does not match the dataset audit contract."
            )
        normalized: dict[str, str] = {}
        for key, value in fingerprints.items():
            digest = str(value).strip().lower()
            if _SHA256_RE.fullmatch(digest) is None:
                raise ValueError(
                    "source manifest fingerprints must contain exactly 64 hexadecimal characters."
                )
            normalized[str(key)] = digest
        object.__setattr__(self, "source_manifest_fingerprints_sha256", normalized)

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic JSON-compatible receipt."""
        payload = asdict(self)
        payload["record_type"] = _RECORD_TYPE
        payload["source_manifest_fingerprints_sha256"] = dict(
            self.source_manifest_fingerprints_sha256
        )
        payload["scientific_boundary"] = dict(_SCIENTIFIC_BOUNDARY)
        payload["receipt_fingerprint_sha256"] = benchmark_fingerprint(payload)
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SourceAuditLineageReceipt:
        """Load a receipt only after validating its own fingerprint and boundary."""
        values = dict(payload)
        if values.get("record_type") != _RECORD_TYPE:
            raise BenchmarkIntegrityError(
                f"Source-audit lineage record_type must be {_RECORD_TYPE!r}."
            )
        if values.get("scientific_boundary") != _SCIENTIFIC_BOUNDARY:
            raise BenchmarkIntegrityError(
                "Source-audit lineage scientific_boundary must preserve claim limits."
            )
        observed = values.pop("receipt_fingerprint_sha256", None)
        if not isinstance(observed, str) or _SHA256_RE.fullmatch(observed.lower()) is None:
            raise BenchmarkIntegrityError(
                "Source-audit lineage receipt_fingerprint_sha256 is invalid."
            )
        expected = benchmark_fingerprint(values)
        if observed.lower() != expected:
            raise BenchmarkIntegrityError("Source-audit lineage receipt fingerprint mismatch.")
        values.pop("record_type", None)
        values.pop("scientific_boundary", None)
        try:
            return cls(**values)
        except (TypeError, ValueError) as exc:
            raise BenchmarkIntegrityError("Source-audit lineage receipt is invalid.") from exc


def _dataset_key(spec: AuditTemplateSpec) -> str:
    if isinstance(spec, Hollywood2SourceAuditSpec):
        return "hollywood2em"
    if isinstance(spec, GazeInWildSourceAuditSpec):
        return "gaze-in-the-wild"
    raise TypeError("spec must be a Hollywood2SourceAuditSpec or GazeInWildSourceAuditSpec.")


def _require_mapping(value: Any, *, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(f"Audit report {field_name} must be a JSON object.")
    return value


def _validate_report_fingerprint(report: Mapping[str, Any]) -> str:
    observed = report.get("report_fingerprint_sha256")
    if not isinstance(observed, str) or _SHA256_RE.fullmatch(observed.lower()) is None:
        raise BenchmarkIntegrityError("Audit report fingerprint is missing or invalid.")
    body = dict(report)
    body.pop("report_fingerprint_sha256", None)
    expected = benchmark_fingerprint(body)
    if observed.lower() != expected:
        raise BenchmarkIntegrityError("Audit report fingerprint mismatch.")
    return expected


def _validate_common_report(
    report: Mapping[str, Any],
    *,
    authorized_spec: AuditTemplateSpec,
    dataset_key: str,
) -> str:
    expected_audit = (
        "Hollywood2EM-source-audit"
        if dataset_key == "hollywood2em"
        else "Gaze-in-the-Wild-source-audit"
    )
    if report.get("audit") != expected_audit or report.get("status") != "verified":
        raise BenchmarkIntegrityError(
            "Audit lineage requires the expected dataset-specific verified source-audit report."
        )
    report_fingerprint = _validate_report_fingerprint(report)
    expected_spec_fingerprint = benchmark_fingerprint(authorized_spec.to_dict())
    if report.get("spec_fingerprint_sha256") != expected_spec_fingerprint:
        raise BenchmarkIntegrityError(
            "Audit report is not bound to the exact authorized empirical specification."
        )

    dataset = _require_mapping(report.get("dataset"), field_name="dataset")
    if dataset.get("source_revision") != authorized_spec.source_revision:
        raise BenchmarkIntegrityError("Audit report source revision does not match the spec.")
    reuse = _require_mapping(report.get("reuse"), field_name="reuse")
    if reuse.get("terms_verified") is not True or reuse.get("analysis_use_permitted") is not True:
        raise BenchmarkIntegrityError(
            "Audit lineage requires verified reuse terms and permitted analysis use."
        )
    coordinates = _require_mapping(report.get("coordinates"), field_name="coordinates")
    if coordinates.get("verified") is not True:
        raise BenchmarkIntegrityError("Audit lineage requires verified coordinate units.")
    return report_fingerprint


def _manifest_fingerprints(
    report: Mapping[str, Any],
    *,
    dataset_key: str,
) -> dict[str, str]:
    if dataset_key == "hollywood2em":
        inventory = _require_mapping(report.get("source_inventory"), field_name="source_inventory")
        if inventory.get("exact_inventory_match") is not True:
            raise BenchmarkIntegrityError(
                "Hollywood2EM audit report lacks an exact inventory match."
            )
        digest = inventory.get("source_manifest_fingerprint_sha256")
        if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest.lower()) is None:
            raise BenchmarkIntegrityError("Hollywood2EM source manifest fingerprint is invalid.")
        annotations = _require_mapping(report.get("annotations"), field_name="annotations")
        if annotations.get("same_underlying_gaze_verified") is not True:
            raise BenchmarkIntegrityError(
                "Hollywood2EM lineage requires verified shared gaze for student/expert labels."
            )
        identity = _require_mapping(
            report.get("participant_identity"), field_name="participant_identity"
        )
        if identity.get("verified") is not True:
            raise BenchmarkIntegrityError(
                "Hollywood2EM lineage requires verified participant identity mapping."
            )
        sampling = _require_mapping(report.get("sampling"), field_name="sampling")
        if sampling.get("sampling_origin") != "native":
            raise BenchmarkIntegrityError("Hollywood2EM audit sampling must remain native.")
        return {"source": digest.lower()}

    label_inventory = _require_mapping(report.get("label_inventory"), field_name="label_inventory")
    process_inventory = _require_mapping(
        report.get("process_inventory"), field_name="process_inventory"
    )
    if (
        label_inventory.get("exact_inventory_match") is not True
        or process_inventory.get("exact_inventory_match") is not True
    ):
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild audit report lacks exact label/process inventory matches."
        )
    identity = _require_mapping(report.get("identity"), field_name="identity")
    if identity.get("participant_mapping_verified") is not True:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild lineage requires verified participant mapping."
        )
    sampling = _require_mapping(report.get("sampling"), field_name="sampling")
    if sampling.get("source") != "inferred_from_LabelData.T_per_file":
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild audit lineage must preserve timestamp-inferred file cadence."
        )
    result: dict[str, str] = {}
    for key, inventory in (("label", label_inventory), ("process", process_inventory)):
        digest = inventory.get("manifest_fingerprint_sha256")
        if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest.lower()) is None:
            raise BenchmarkIntegrityError(
                f"Gaze-in-the-Wild {key} manifest fingerprint is invalid."
            )
        result[key] = digest.lower()
    return result


def build_source_audit_lineage_receipt(
    template_spec: AuditTemplateSpec,
    authorization: CandidateSourceAuditAuthorization,
    audit_report: Mapping[str, Any],
) -> SourceAuditLineageReceipt:
    """Verify and bind the full reviewed-template → authorization → source-audit chain.

    The function recomputes the authorized empirical specification deterministically from the
    original template and authorization, then requires the audit report to fingerprint that exact
    specification and to pass dataset-specific source-audit invariants. It creates no new model,
    agreement, AOI, native-GP3, or Frozen Evidence result.
    """
    dataset_key = _dataset_key(template_spec)
    if template_spec.dataset_status != "template":
        raise BenchmarkIntegrityError("Lineage must start from dataset_status='template'.")
    if not isinstance(authorization, CandidateSourceAuditAuthorization):
        raise TypeError("authorization must be a CandidateSourceAuditAuthorization instance.")
    if authorization.decision != "authorized":
        raise BenchmarkIntegrityError("Lineage requires an explicit authorized decision.")
    if not isinstance(audit_report, Mapping):
        raise TypeError("audit_report must be a mapping.")

    authorized_spec = authorize_candidate_source_audit_template(template_spec, authorization)
    report_fingerprint = _validate_common_report(
        audit_report,
        authorized_spec=authorized_spec,
        dataset_key=dataset_key,
    )
    manifests = _manifest_fingerprints(audit_report, dataset_key=dataset_key)
    template_fingerprint = source_audit_template_fingerprint(template_spec)
    authorization_fingerprint = benchmark_fingerprint(authorization.to_dict())
    authorized_spec_fingerprint = benchmark_fingerprint(authorized_spec.to_dict())

    return SourceAuditLineageReceipt(
        dataset_key=dataset_key,
        audit_template_fingerprint_sha256=template_fingerprint,
        authorization_fingerprint_sha256=authorization_fingerprint,
        authorized_spec_fingerprint_sha256=authorized_spec_fingerprint,
        audit_report_fingerprint_sha256=report_fingerprint,
        source_manifest_fingerprints_sha256=manifests,
        source_revision=authorized_spec.source_revision,
    )


def write_source_audit_lineage_receipt(
    receipt: SourceAuditLineageReceipt,
    path: str | Path,
    *,
    candidate_root: str | Path,
    overwrite: bool = False,
) -> Path:
    """Write one verified lineage receipt outside the candidate source tree."""
    if not isinstance(receipt, SourceAuditLineageReceipt):
        raise TypeError("receipt must be a SourceAuditLineageReceipt instance.")
    root = Path(candidate_root).resolve()
    target = Path(path)
    resolved_target = target.resolve(strict=False)
    if resolved_target == root or root in resolved_target.parents:
        raise BenchmarkIntegrityError(
            "Source-audit lineage receipt must be written outside the candidate source tree."
        )
    if target.exists() and not overwrite:
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(receipt.to_dict(), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return target


def load_source_audit_lineage_receipt(path: str | Path) -> SourceAuditLineageReceipt:
    """Load and self-validate a saved source-audit lineage receipt."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(
            "Source-audit lineage receipt must be valid UTF-8 JSON."
        ) from exc
    if not isinstance(payload, Mapping):
        raise BenchmarkIntegrityError("Source-audit lineage receipt must contain one JSON object.")
    return SourceAuditLineageReceipt.from_dict(payload)
