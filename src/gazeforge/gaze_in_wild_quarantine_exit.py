"""Explicit exit gate from Gaze-in-the-Wild recovery quarantine to source-audit review.

The gate is deliberately narrower than a source audit. It binds one exact recovery
candidate, one exact generic candidate inventory, and one exact non-empirical audit
template to an independently reviewed source-authority / exact-copy / rights decision.
It never executes the source audit and never creates empirical evidence.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .benchmarks import benchmark_fingerprint
from .exceptions import BenchmarkIntegrityError
from .gaze_in_wild_audit import GazeInWildSourceAuditSpec
from .gaze_in_wild_recovery import (
    recovery_candidate_record_fingerprint,
    validate_gaze_in_wild_recovery_candidate_review,
    verify_gaze_in_wild_recovery_candidate_tree,
)
from .source_candidate import CandidateSourceInventory, build_candidate_source_inventory

_RECORD_TYPE = "gaze-in-wild-recovery-quarantine-exit-v1"
_ALLOWED_DECISIONS = {"pending", "authorized", "denied"}
_ALLOWED_REDISTRIBUTION = {"permitted", "restricted", "unknown"}
_EXIT_ELIGIBLE_CANDIDATE_KINDS = {
    "unknown_recovered_copy",
    "candidate_original_layout_unverified",
}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_UNRESOLVED = {"", "review_required", "__unresolved__", "unknown", "none", "nan"}
_SCIENTIFIC_BOUNDARY = {
    "quarantine_exit_review_only": True,
    "source_audit_execution_authorized_by_this_record": False,
    "source_audit_executed": False,
    "participant_mapping_verified": False,
    "coordinate_unit_verified": False,
    "sampling_cadence_verified": False,
    "independent_labeller_recoverability_verified": False,
    "human_human_agreement_created": False,
    "participant_disjoint_model_validation_created": False,
    "cross_dataset_performance_created": False,
    "gp3_validity_created": False,
    "frozen_evidence_performance_claim_created": False,
    "empirical_evidence_created": False,
}


def _sha256(value: Any, *, field_name: str) -> str:
    digest = str(value).strip().lower()
    if _SHA256_RE.fullmatch(digest) is None:
        raise ValueError(f"{field_name} must contain exactly 64 hexadecimal characters.")
    return digest


def _resolved(value: Any, *, field_name: str) -> str:
    text = "" if value is None else str(value).strip()
    if text.lower() in _UNRESOLVED:
        raise BenchmarkIntegrityError(
            f"Authorized quarantine exits require reviewed {field_name}."
        )
    return text


def _load_json_object(
    value: Mapping[str, Any] | str | Path,
    *,
    label: str,
) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    path = Path(value)
    if not path.is_file():
        raise FileNotFoundError(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(f"{label} must be valid UTF-8 JSON.") from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(f"{label} must contain one JSON object.")
    return payload


def _template_fingerprint(spec: GazeInWildSourceAuditSpec) -> str:
    if not isinstance(spec, GazeInWildSourceAuditSpec):
        raise TypeError("spec must be a GazeInWildSourceAuditSpec instance.")
    if spec.dataset_status != "template":
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild quarantine exit must bind a dataset_status='template' audit spec."
        )
    return benchmark_fingerprint(spec.to_dict())


def _candidate_inventory_note(fingerprint: str) -> str:
    return f"Candidate inventory fingerprint: {fingerprint}"


def _recovery_files(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    inventory = record.get("inventory")
    if not isinstance(inventory, Mapping):
        raise BenchmarkIntegrityError("GIW recovery review inventory is missing.")
    raw = inventory.get("files")
    if not isinstance(raw, list):
        raise BenchmarkIntegrityError("GIW recovery review file manifest is missing.")
    rows: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            raise BenchmarkIntegrityError("GIW recovery review file manifest is invalid.")
        rows.append(
            {
                "path": str(item["path"]),
                "sha256": str(item["sha256"]),
                "bytes": int(item["bytes"]),
            }
        )
    return rows


def _generic_inventory_files(inventory: CandidateSourceInventory) -> list[dict[str, Any]]:
    return [
        {"path": item.path, "sha256": item.sha256, "bytes": item.bytes}
        for item in inventory.files
    ]


def _validate_candidate_binding(
    root: str | Path,
    recovery_record_or_path: Mapping[str, Any] | str | Path,
    inventory: CandidateSourceInventory,
    spec: GazeInWildSourceAuditSpec,
) -> tuple[dict[str, Any], CandidateSourceInventory, str]:
    if not isinstance(inventory, CandidateSourceInventory):
        raise TypeError("inventory must be a CandidateSourceInventory instance.")
    if inventory.dataset_key != "gaze-in-the-wild":
        raise BenchmarkIntegrityError(
            "GIW quarantine exit requires a Gaze-in-the-Wild inventory."
        )

    root_path = Path(root).resolve()
    recovery = _load_json_object(
        recovery_record_or_path,
        label="Gaze-in-the-Wild recovery candidate review",
    )
    validate_gaze_in_wild_recovery_candidate_review(recovery)
    verify_gaze_in_wild_recovery_candidate_tree(root_path, recovery)

    current = build_candidate_source_inventory(root_path, dataset_key="gaze-in-the-wild")
    if current.inventory_fingerprint_sha256 != inventory.inventory_fingerprint_sha256:
        raise BenchmarkIntegrityError(
            "GIW quarantine exit inventory no longer matches the current candidate tree."
        )
    if current.files != inventory.files:
        raise BenchmarkIntegrityError(
            "GIW quarantine exit inventory file manifest no longer matches the candidate tree."
        )
    if _recovery_files(recovery) != _generic_inventory_files(inventory):
        raise BenchmarkIntegrityError(
            "GIW recovery review and generic candidate inventory do not describe the exact same "
            "path/hash/byte manifest."
        )

    template_fingerprint = _template_fingerprint(spec)
    expected_note = _candidate_inventory_note(inventory.inventory_fingerprint_sha256)
    if expected_note not in spec.notes:
        raise BenchmarkIntegrityError(
            "GIW audit template is not bound to the reviewed candidate inventory fingerprint."
        )
    return recovery, current, template_fingerprint


@dataclass(frozen=True, slots=True)
class GazeInWildQuarantineExitAuthorization:
    """Manual recovery-quarantine exit decision bound to exact source identities."""

    recovery_candidate_kind: str
    recovery_record_fingerprint_sha256: str
    recovery_tree_fingerprint_sha256: str
    candidate_inventory_fingerprint_sha256: str
    audit_template_fingerprint_sha256: str
    decision: str = "pending"
    reviewer: str = "REVIEW_REQUIRED"
    reviewed_at: str = "REVIEW_REQUIRED"
    source_authority_verified: bool = False
    authoritative_source: str = "REVIEW_REQUIRED"
    authoritative_source_revision: str = "REVIEW_REQUIRED"
    source_authority_evidence: str = "REVIEW_REQUIRED"
    exact_copy_identity_verified: bool = False
    exact_copy_identity_evidence: str = "REVIEW_REQUIRED"
    dataset_file_rights_resolved: bool = False
    reuse_terms_verified: bool = False
    reuse_terms_source: str = "REVIEW_REQUIRED"
    rights_evidence: str = "REVIEW_REQUIRED"
    analysis_use_permitted: bool = False
    analysis_use_evidence: str = "REVIEW_REQUIRED"
    redistribution_status: str = "unknown"
    redistribution_evidence: str = "REVIEW_REQUIRED"
    authorization_basis: str = "REVIEW_REQUIRED"
    notes: tuple[str, ...] = ()
    _binding_validated: bool = field(default=False, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        kind = str(self.recovery_candidate_kind).strip().lower()
        object.__setattr__(self, "recovery_candidate_kind", kind)
        for field_name in (
            "recovery_record_fingerprint_sha256",
            "recovery_tree_fingerprint_sha256",
            "candidate_inventory_fingerprint_sha256",
            "audit_template_fingerprint_sha256",
        ):
            object.__setattr__(
                self,
                field_name,
                _sha256(getattr(self, field_name), field_name=field_name),
            )
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
        object.__setattr__(self, "notes", tuple(str(note) for note in self.notes))

        for field_name in (
            "source_authority_verified",
            "exact_copy_identity_verified",
            "dataset_file_rights_resolved",
            "reuse_terms_verified",
            "analysis_use_permitted",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise ValueError(f"{field_name} must be boolean.")

        if decision == "authorized":
            self._require_authorized()
        elif decision == "denied":
            for field_name in ("reviewer", "reviewed_at", "authorization_basis"):
                _resolved(getattr(self, field_name), field_name=field_name)

    def _require_authorized(self) -> None:
        if self.recovery_candidate_kind not in _EXIT_ELIGIBLE_CANDIDATE_KINDS:
            raise BenchmarkIntegrityError(
                "Transformed-secondary and labeller-provenance-only GIW candidates cannot leave "
                "quarantine. Rebuild the candidate review from the independently verified exact "
                "copy if its scientific identity changes."
            )
        required_true = (
            "source_authority_verified",
            "exact_copy_identity_verified",
            "dataset_file_rights_resolved",
            "reuse_terms_verified",
            "analysis_use_permitted",
        )
        missing = [name for name in required_true if not getattr(self, name)]
        if missing:
            raise BenchmarkIntegrityError(
                "Authorized GIW quarantine exits require affirmative authority/exact-copy/rights "
                f"gates: {missing}."
            )
        if self.redistribution_status == "unknown":
            raise BenchmarkIntegrityError(
                "Authorized GIW quarantine exits require reviewed redistribution_status."
            )
        for field_name in (
            "reviewer",
            "reviewed_at",
            "authoritative_source",
            "authoritative_source_revision",
            "source_authority_evidence",
            "exact_copy_identity_evidence",
            "reuse_terms_source",
            "rights_evidence",
            "analysis_use_evidence",
            "redistribution_evidence",
            "authorization_basis",
        ):
            _resolved(getattr(self, field_name), field_name=field_name)

    @property
    def record_fingerprint_sha256(self) -> str:
        """Canonical identity of the complete reviewed decision."""
        return benchmark_fingerprint(self._payload_without_fingerprint())

    def _payload_without_fingerprint(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("_binding_validated", None)
        payload["record_type"] = _RECORD_TYPE
        payload["notes"] = list(self.notes)
        payload["scientific_boundary"] = dict(_SCIENTIFIC_BOUNDARY)
        return payload

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload_without_fingerprint()
        payload["record_fingerprint_sha256"] = self.record_fingerprint_sha256
        return payload

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> GazeInWildQuarantineExitAuthorization:
        if payload.get("record_type") != _RECORD_TYPE:
            raise BenchmarkIntegrityError(
                f"GIW quarantine-exit record_type must be {_RECORD_TYPE!r}."
            )
        if payload.get("scientific_boundary") != _SCIENTIFIC_BOUNDARY:
            raise BenchmarkIntegrityError(
                "GIW quarantine-exit scientific boundary cannot be promoted."
            )
        values = dict(payload)
        stored = str(values.pop("record_fingerprint_sha256", "")).strip().lower()
        values.pop("record_type", None)
        values.pop("scientific_boundary", None)
        if "notes" in values:
            if not isinstance(values["notes"], list):
                raise BenchmarkIntegrityError("GIW quarantine-exit notes must be a JSON list.")
            values["notes"] = tuple(values["notes"])
        try:
            record = cls(**values)
        except (TypeError, ValueError) as exc:
            raise BenchmarkIntegrityError("GIW quarantine-exit record is invalid.") from exc
        if stored != record.record_fingerprint_sha256:
            raise BenchmarkIntegrityError("GIW quarantine-exit record fingerprint drifted.")
        return record


def _validate_authorized_template_consistency(
    authorization: GazeInWildQuarantineExitAuthorization,
    spec: GazeInWildSourceAuditSpec,
) -> None:
    if authorization.decision != "authorized":
        return
    authorization._require_authorized()
    expected = {
        "authoritative_source": spec.source,
        "authoritative_source_revision": spec.source_revision,
        "reuse_terms_source": spec.reuse_terms_source,
    }
    for field_name, expected_value in expected.items():
        if getattr(authorization, field_name) != expected_value:
            raise BenchmarkIntegrityError(
                "GIW quarantine-exit reviewed source/rights identity conflicts with the exact "
                f"audit template field {field_name}."
            )


def build_gaze_in_wild_quarantine_exit_authorization(
    root: str | Path,
    recovery_record_or_path: Mapping[str, Any] | str | Path,
    inventory: CandidateSourceInventory,
    spec: GazeInWildSourceAuditSpec,
) -> GazeInWildQuarantineExitAuthorization:
    """Create a pending exit record after exact recovery/inventory/template binding checks."""
    recovery, current, template_fingerprint = _validate_candidate_binding(
        root,
        recovery_record_or_path,
        inventory,
        spec,
    )
    recovery_inventory = recovery["inventory"]
    return GazeInWildQuarantineExitAuthorization(
        recovery_candidate_kind=str(recovery["candidate_kind"]),
        recovery_record_fingerprint_sha256=recovery_candidate_record_fingerprint(recovery),
        recovery_tree_fingerprint_sha256=str(recovery_inventory["tree_fingerprint_sha256"]),
        candidate_inventory_fingerprint_sha256=current.inventory_fingerprint_sha256,
        audit_template_fingerprint_sha256=template_fingerprint,
        notes=(
            "Pending independent quarantine-exit review. This record does not execute a source "
            "audit or create empirical evidence.",
        ),
    )


def write_gaze_in_wild_quarantine_exit_authorization(
    authorization: GazeInWildQuarantineExitAuthorization,
    path: str | Path,
    *,
    candidate_root: str | Path,
    overwrite: bool = False,
) -> Path:
    """Write one exit record outside the candidate tree."""
    if not isinstance(authorization, GazeInWildQuarantineExitAuthorization):
        raise TypeError("authorization must be a GazeInWildQuarantineExitAuthorization instance.")
    root = Path(candidate_root).resolve()
    target = Path(path)
    resolved_target = target.resolve(strict=False)
    if resolved_target == root or root in resolved_target.parents:
        raise BenchmarkIntegrityError(
            "GIW quarantine-exit output must be outside the candidate source tree."
        )
    if target.exists() and not overwrite:
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(authorization.to_dict(), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return target


def load_gaze_in_wild_quarantine_exit_authorization(
    path: str | Path,
) -> GazeInWildQuarantineExitAuthorization:
    payload = _load_json_object(
        path,
        label="Gaze-in-the-Wild quarantine-exit authorization",
    )
    return GazeInWildQuarantineExitAuthorization.from_dict(payload)


def validate_gaze_in_wild_quarantine_exit_authorization(
    authorization_or_path: GazeInWildQuarantineExitAuthorization | str | Path,
    *,
    root: str | Path,
    recovery_record_or_path: Mapping[str, Any] | str | Path,
    inventory: CandidateSourceInventory,
    spec: GazeInWildSourceAuditSpec,
) -> GazeInWildQuarantineExitAuthorization:
    """Revalidate the exit record against the current exact candidate and audit template."""
    authorization = (
        authorization_or_path
        if isinstance(authorization_or_path, GazeInWildQuarantineExitAuthorization)
        else load_gaze_in_wild_quarantine_exit_authorization(authorization_or_path)
    )
    recovery, current, template_fingerprint = _validate_candidate_binding(
        root,
        recovery_record_or_path,
        inventory,
        spec,
    )
    if authorization.recovery_candidate_kind != str(recovery["candidate_kind"]):
        raise BenchmarkIntegrityError("GIW quarantine-exit candidate kind drifted.")
    if (
        authorization.recovery_record_fingerprint_sha256
        != recovery_candidate_record_fingerprint(recovery)
    ):
        raise BenchmarkIntegrityError("GIW quarantine-exit recovery-record identity drifted.")
    if authorization.recovery_tree_fingerprint_sha256 != str(
        recovery["inventory"]["tree_fingerprint_sha256"]
    ):
        raise BenchmarkIntegrityError("GIW quarantine-exit recovery-tree identity drifted.")
    if (
        authorization.candidate_inventory_fingerprint_sha256
        != current.inventory_fingerprint_sha256
    ):
        raise BenchmarkIntegrityError("GIW quarantine-exit candidate-inventory identity drifted.")
    if authorization.audit_template_fingerprint_sha256 != template_fingerprint:
        raise BenchmarkIntegrityError("GIW quarantine-exit audit-template identity drifted.")
    _validate_authorized_template_consistency(authorization, spec)
    object.__setattr__(authorization, "_binding_validated", True)
    return authorization


def require_authorized_gaze_in_wild_quarantine_exit(
    authorization: GazeInWildQuarantineExitAuthorization,
    spec: GazeInWildSourceAuditSpec,
) -> None:
    """Require a freshly validated authorized exit bound to one exact GIW audit template.

    Full candidate-tree/recovery revalidation is performed by
    :func:`validate_gaze_in_wild_quarantine_exit_authorization`. The validation state is ephemeral:
    it is not serialized, and editing/reloading a record requires another complete validation before
    the generic source-audit authorization boundary will accept it.
    """
    if not isinstance(authorization, GazeInWildQuarantineExitAuthorization):
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild source-audit authorization requires a validated quarantine-exit "
            "record."
        )
    if authorization._binding_validated is not True:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild quarantine-exit record must be freshly revalidated against the "
            "current candidate tree, recovery review, candidate inventory, and audit template."
        )
    if authorization.decision != "authorized":
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild recovery quarantine must be explicitly authorized before an "
            "empirical source-audit spec can be materialized."
        )
    authorization._require_authorized()
    if authorization.audit_template_fingerprint_sha256 != _template_fingerprint(spec):
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild quarantine-exit authorization is not bound to this exact audit "
            "template."
        )
    _validate_authorized_template_consistency(authorization, spec)
