"""Explicit human authorization gate between reviewed templates and empirical source audits."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .benchmarks import benchmark_fingerprint
from .exceptions import BenchmarkIntegrityError
from .gaze_in_wild_audit import GazeInWildSourceAuditSpec
from .gaze_in_wild_quarantine_exit import (
    GazeInWildQuarantineExitAuthorization,
    require_authorized_gaze_in_wild_quarantine_exit,
)
from .hollywood2_audit import Hollywood2SourceAuditSpec

AuditTemplateSpec = Hollywood2SourceAuditSpec | GazeInWildSourceAuditSpec

_RECORD_TYPE = "candidate-source-audit-authorization-v1"
_ALLOWED_DATASETS = {"hollywood2em", "gaze-in-the-wild"}
_ALLOWED_DECISIONS = {"pending", "authorized", "denied"}
_ALLOWED_REDISTRIBUTION = {"permitted", "restricted", "unknown"}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_UNRESOLVED = {"", "review_required", "__unresolved__", "unknown", "none", "nan"}
_SCIENTIFIC_BOUNDARY = {
    "manual_authorization_required": True,
    "automatic_evidence_inference": False,
    "source_audit_executed": False,
    "empirical_evidence_created": False,
}


@dataclass(frozen=True, slots=True)
class CandidateSourceAuditAuthorization:
    """Manual decision record bound to one exact non-empirical audit template."""

    dataset_key: str
    audit_template_fingerprint_sha256: str
    decision: str = "pending"
    reviewer: str = "REVIEW_REQUIRED"
    reviewed_at: str = "REVIEW_REQUIRED"
    source_authority_verified: bool = False
    source_authority_evidence: str = "REVIEW_REQUIRED"
    reuse_terms_verified: bool = False
    reuse_terms_evidence: str = "REVIEW_REQUIRED"
    analysis_use_permitted: bool = False
    analysis_use_evidence: str = "REVIEW_REQUIRED"
    redistribution_status: str = "unknown"
    redistribution_evidence: str = "REVIEW_REQUIRED"
    coordinate_unit_verified: bool = False
    coordinate_verification_evidence: str = "REVIEW_REQUIRED"
    participant_mapping_verified: bool = False
    participant_mapping_evidence: str = "REVIEW_REQUIRED"
    sampling_contract_reviewed: bool = False
    sampling_contract_evidence: str = "REVIEW_REQUIRED"
    annotation_contract_reviewed: bool = False
    annotation_contract_evidence: str = "REVIEW_REQUIRED"
    pixel_kinematics_compatible: bool = False
    authorization_basis: str = "REVIEW_REQUIRED"
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        dataset_key = str(self.dataset_key).strip().lower()
        if dataset_key not in _ALLOWED_DATASETS:
            raise ValueError("Unsupported source-audit authorization dataset key.")
        object.__setattr__(self, "dataset_key", dataset_key)

        fingerprint = str(self.audit_template_fingerprint_sha256).strip().lower()
        if _SHA256_RE.fullmatch(fingerprint) is None:
            raise ValueError(
                "audit_template_fingerprint_sha256 must contain exactly 64 hexadecimal characters."
            )
        object.__setattr__(self, "audit_template_fingerprint_sha256", fingerprint)

        decision = str(self.decision).strip().lower()
        if decision not in _ALLOWED_DECISIONS:
            raise ValueError("decision must be 'pending', 'authorized', or 'denied'.")
        object.__setattr__(self, "decision", decision)

        redistribution = str(self.redistribution_status).strip().lower()
        if redistribution not in _ALLOWED_REDISTRIBUTION:
            raise ValueError(
                "redistribution_status must be 'permitted', 'restricted', or 'unknown'."
            )
        object.__setattr__(self, "redistribution_status", redistribution)

        bool_fields = (
            "source_authority_verified",
            "reuse_terms_verified",
            "analysis_use_permitted",
            "coordinate_unit_verified",
            "participant_mapping_verified",
            "sampling_contract_reviewed",
            "annotation_contract_reviewed",
            "pixel_kinematics_compatible",
        )
        for field_name in bool_fields:
            if not isinstance(getattr(self, field_name), bool):
                raise ValueError(f"{field_name} must be boolean.")

        notes = tuple(str(note) for note in self.notes)
        object.__setattr__(self, "notes", notes)
        if dataset_key == "hollywood2em" and self.pixel_kinematics_compatible:
            raise ValueError(
                "pixel_kinematics_compatible is only an authorization control for "
                "Gaze-in-the-Wild."
            )
        if decision == "authorized":
            _require_authorized_fields(self)
        elif decision == "denied":
            for field_name in ("reviewer", "reviewed_at", "authorization_basis"):
                _require_resolved_text(getattr(self, field_name), field_name=field_name)

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic JSON-compatible authorization record."""
        payload = asdict(self)
        payload["record_type"] = _RECORD_TYPE
        payload["notes"] = list(self.notes)
        payload["scientific_boundary"] = dict(_SCIENTIFIC_BOUNDARY)
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> CandidateSourceAuditAuthorization:
        """Construct an authorization after record and boundary validation."""
        if payload.get("record_type") != _RECORD_TYPE:
            raise BenchmarkIntegrityError(
                f"Source-audit authorization record_type must be {_RECORD_TYPE!r}."
            )
        if payload.get("scientific_boundary") != _SCIENTIFIC_BOUNDARY:
            raise BenchmarkIntegrityError(
                "Source-audit authorization scientific_boundary must preserve the manual gate."
            )
        values = dict(payload)
        values.pop("record_type", None)
        values.pop("scientific_boundary", None)
        if "notes" in values:
            if not isinstance(values["notes"], list):
                raise BenchmarkIntegrityError("Authorization notes must be a JSON list.")
            values["notes"] = tuple(values["notes"])
        try:
            return cls(**values)
        except (TypeError, ValueError) as exc:
            raise BenchmarkIntegrityError("Source-audit authorization record is invalid.") from exc


def _require_resolved_text(value: Any, *, field_name: str) -> str:
    text = "" if value is None else str(value).strip()
    if text.lower() in _UNRESOLVED:
        raise BenchmarkIntegrityError(
            f"Authorized source-audit decisions require reviewed {field_name}."
        )
    return text


def _require_authorized_fields(authorization: CandidateSourceAuditAuthorization) -> None:
    required_true = (
        "source_authority_verified",
        "reuse_terms_verified",
        "analysis_use_permitted",
        "coordinate_unit_verified",
        "participant_mapping_verified",
        "sampling_contract_reviewed",
        "annotation_contract_reviewed",
    )
    missing = [name for name in required_true if not getattr(authorization, name)]
    if missing:
        raise BenchmarkIntegrityError(
            "Authorized source-audit decisions require affirmative manual review gates: "
            f"{missing}."
        )

    evidence_fields = (
        "reviewer",
        "reviewed_at",
        "source_authority_evidence",
        "reuse_terms_evidence",
        "analysis_use_evidence",
        "redistribution_evidence",
        "coordinate_verification_evidence",
        "participant_mapping_evidence",
        "sampling_contract_evidence",
        "annotation_contract_evidence",
        "authorization_basis",
    )
    for field_name in evidence_fields:
        _require_resolved_text(getattr(authorization, field_name), field_name=field_name)


def _dataset_key(spec: AuditTemplateSpec) -> str:
    if isinstance(spec, Hollywood2SourceAuditSpec):
        return "hollywood2em"
    if isinstance(spec, GazeInWildSourceAuditSpec):
        return "gaze-in-the-wild"
    raise TypeError("spec must be a Hollywood2SourceAuditSpec or GazeInWildSourceAuditSpec.")


def source_audit_template_fingerprint(spec: AuditTemplateSpec) -> str:
    """Fingerprint one complete source-audit template deterministically."""
    _dataset_key(spec)
    return benchmark_fingerprint(spec.to_dict())


def build_candidate_source_audit_authorization(
    spec: AuditTemplateSpec,
) -> CandidateSourceAuditAuthorization:
    """Create a pending manual authorization record bound to one exact audit template."""
    dataset_key = _dataset_key(spec)
    if spec.dataset_status != "template":
        raise BenchmarkIntegrityError(
            "Authorization scaffolds can only be built for dataset_status='template' specs."
        )
    return CandidateSourceAuditAuthorization(
        dataset_key=dataset_key,
        audit_template_fingerprint_sha256=source_audit_template_fingerprint(spec),
        notes=(
            "Pending manual authorization. This record does not execute a source audit or create "
            "empirical evidence.",
        ),
    )


def write_candidate_source_audit_authorization(
    authorization: CandidateSourceAuditAuthorization,
    path: str | Path,
    *,
    candidate_root: str | Path,
    overwrite: bool = False,
) -> Path:
    """Write an authorization record outside the candidate source tree."""
    if not isinstance(authorization, CandidateSourceAuditAuthorization):
        raise TypeError("authorization must be a CandidateSourceAuditAuthorization instance.")
    root = Path(candidate_root).resolve()
    target = Path(path)
    resolved_target = target.resolve(strict=False)
    if resolved_target == root or root in resolved_target.parents:
        raise BenchmarkIntegrityError(
            "Source-audit authorization output must be outside the candidate source tree."
        )
    if target.exists() and not overwrite:
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(authorization.to_dict(), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return target


def load_candidate_source_audit_authorization(
    path: str | Path,
) -> CandidateSourceAuditAuthorization:
    """Load one manual source-audit authorization JSON record."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(
            "Source-audit authorization must be valid UTF-8 JSON."
        ) from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError("Source-audit authorization must contain one JSON object.")
    return CandidateSourceAuditAuthorization.from_dict(payload)


def validate_candidate_source_audit_authorization(
    authorization_path: str | Path,
    spec: AuditTemplateSpec,
) -> CandidateSourceAuditAuthorization:
    """Validate one manual decision against the exact template it reviews."""
    authorization = load_candidate_source_audit_authorization(authorization_path)
    _validate_authorization_binding(spec, authorization)
    return authorization


def _validate_authorization_binding(
    spec: AuditTemplateSpec,
    authorization: CandidateSourceAuditAuthorization,
) -> None:
    dataset_key = _dataset_key(spec)
    if spec.dataset_status != "template":
        raise BenchmarkIntegrityError(
            "Source-audit authorization must be bound to a non-empirical template."
        )
    if authorization.dataset_key != dataset_key:
        raise BenchmarkIntegrityError("Authorization dataset identity does not match the template.")
    observed = source_audit_template_fingerprint(spec)
    if authorization.audit_template_fingerprint_sha256 != observed:
        raise BenchmarkIntegrityError(
            "Authorization is not bound to the current exact audit-template fingerprint."
        )
    if (
        dataset_key == "gaze-in-the-wild"
        and authorization.pixel_kinematics_compatible
        and spec.coordinate_unit.lower() != "pixels"
    ):
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild pixel kinematics can only be authorized for verified pixel units."
        )


def authorize_candidate_source_audit_template(
    spec: AuditTemplateSpec,
    authorization: CandidateSourceAuditAuthorization,
    *,
    gaze_in_wild_quarantine_exit: GazeInWildQuarantineExitAuthorization | None = None,
) -> AuditTemplateSpec:
    """Materialize an empirical audit spec from separately reviewed authorization decisions.

    This function authorizes execution of the existing source audit. It does not execute that
    audit, does not verify the local data copy, and does not create agreement or model evidence.
    Recovered Gaze-in-the-Wild candidates additionally require a separately reviewed quarantine-
    exit authorization bound to the exact same audit template.
    """
    if not isinstance(authorization, CandidateSourceAuditAuthorization):
        raise TypeError("authorization must be a CandidateSourceAuditAuthorization instance.")
    _validate_authorization_binding(spec, authorization)
    if authorization.decision != "authorized":
        raise BenchmarkIntegrityError(
            "Only an explicit decision='authorized' can materialize an empirical audit spec."
        )
    _require_authorized_fields(authorization)

    quarantine_exit_fingerprint: str | None = None
    if isinstance(spec, GazeInWildSourceAuditSpec):
        if gaze_in_wild_quarantine_exit is None:
            raise BenchmarkIntegrityError(
                "Gaze-in-the-Wild recovery candidates require a separately authorized quarantine-"
                "exit record before an empirical source-audit spec can be materialized."
            )
        require_authorized_gaze_in_wild_quarantine_exit(
            gaze_in_wild_quarantine_exit,
            spec,
        )
        if authorization.redistribution_status != (
            gaze_in_wild_quarantine_exit.redistribution_status
        ):
            raise BenchmarkIntegrityError(
                "Gaze-in-the-Wild source-audit authorization redistribution status conflicts "
                "with the reviewed recovery-quarantine exit."
            )
        quarantine_exit_fingerprint = gaze_in_wild_quarantine_exit.record_fingerprint_sha256
    elif gaze_in_wild_quarantine_exit is not None:
        raise BenchmarkIntegrityError(
            "A Gaze-in-the-Wild quarantine-exit record cannot authorize a Hollywood2EM template."
        )

    authorization_fingerprint = benchmark_fingerprint(authorization.to_dict())
    notes = list(spec.notes)
    notes.extend(
        [
            "Manual source-audit authorization permits audit execution only; it does not certify "
            "that the source audit passed and does not create empirical metrics by itself.",
            f"Authorization record fingerprint: {authorization_fingerprint}",
            f"Authorization reviewer: {authorization.reviewer}",
            f"Authorization reviewed_at: {authorization.reviewed_at}",
            f"Source-authority authorization evidence: {authorization.source_authority_evidence}",
            f"Reuse-terms authorization evidence: {authorization.reuse_terms_evidence}",
            f"Analysis-use authorization evidence: {authorization.analysis_use_evidence}",
            f"Redistribution authorization evidence: {authorization.redistribution_evidence}",
            (
                "Coordinate authorization evidence: "
                f"{authorization.coordinate_verification_evidence}"
            ),
            (
                "Participant-mapping authorization evidence: "
                f"{authorization.participant_mapping_evidence}"
            ),
            f"Sampling-contract authorization evidence: {authorization.sampling_contract_evidence}",
            (
                "Annotation-contract authorization evidence: "
                f"{authorization.annotation_contract_evidence}"
            ),
            f"Authorization basis: {authorization.authorization_basis}",
        ]
    )
    if quarantine_exit_fingerprint is not None:
        assert gaze_in_wild_quarantine_exit is not None
        notes.extend(
            [
                (
                    "Gaze-in-the-Wild recovery quarantine was exited through a separately "
                    "reviewed authority/exact-copy/rights gate. This still does not mean the "
                    "source audit has passed."
                ),
                f"GIW quarantine-exit record fingerprint: {quarantine_exit_fingerprint}",
                (
                    "GIW quarantine-exit recovery record fingerprint: "
                    f"{gaze_in_wild_quarantine_exit.recovery_record_fingerprint_sha256}"
                ),
                (
                    "GIW quarantine-exit recovery tree fingerprint: "
                    f"{gaze_in_wild_quarantine_exit.recovery_tree_fingerprint_sha256}"
                ),
                (
                    "GIW quarantine-exit candidate inventory fingerprint: "
                    f"{gaze_in_wild_quarantine_exit.candidate_inventory_fingerprint_sha256}"
                ),
            ]
        )

    payload = spec.to_dict()
    payload.update(
        {
            "dataset_status": "empirical",
            "reuse_terms_verified": True,
            "analysis_use_permitted": True,
            "redistribution_status": authorization.redistribution_status,
            "coordinate_unit_verified": True,
            "notes": notes,
        }
    )
    if isinstance(spec, Hollywood2SourceAuditSpec):
        payload["participant_identity_mapping_verified"] = True
        payload["coordinate_verification_basis"] = (
            f"{spec.coordinate_verification_basis} | authorization: "
            f"{authorization.coordinate_verification_evidence}"
        )
        payload["participant_identity_mapping_basis"] = (
            f"{spec.participant_identity_mapping_basis} | authorization: "
            f"{authorization.participant_mapping_evidence}"
        )
        return Hollywood2SourceAuditSpec.from_dict(payload)

    payload["participant_mapping_verified"] = True
    payload["pixel_kinematics_compatible"] = authorization.pixel_kinematics_compatible
    payload["coordinate_verification_basis"] = (
        f"{spec.coordinate_verification_basis} | authorization: "
        f"{authorization.coordinate_verification_evidence}"
    )
    payload["participant_mapping_basis"] = (
        f"{spec.participant_mapping_basis} | authorization: "
        f"{authorization.participant_mapping_evidence}"
    )
    return GazeInWildSourceAuditSpec.from_dict(payload)


def write_authorized_source_audit_spec(
    spec: AuditTemplateSpec,
    path: str | Path,
    *,
    candidate_root: str | Path,
    overwrite: bool = False,
) -> Path:
    """Write an already-authorized empirical source-audit spec outside the candidate tree."""
    _dataset_key(spec)
    if spec.dataset_status != "empirical":
        raise BenchmarkIntegrityError(
            "Authorized source-audit output requires dataset_status='empirical'."
        )
    root = Path(candidate_root).resolve()
    target = Path(path)
    resolved_target = target.resolve(strict=False)
    if resolved_target == root or root in resolved_target.parents:
        raise BenchmarkIntegrityError(
            "Authorized source-audit output must be outside the candidate source tree."
        )
    if target.exists() and not overwrite:
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(spec.to_dict(), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return target
