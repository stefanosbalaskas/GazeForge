"""Fail-closed public evidence-status generation.

This module converts reviewed, versioned evidence policy plus repository artifacts into a
small public status surface. It intentionally does not infer scientific strength from metric
magnitudes. Promotion requires an explicit policy record, exact-byte binding, the declared
evidence fingerprint, and dataset-specific semantic gates.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from .benchmarks import benchmark_fingerprint
from .exceptions import BenchmarkIntegrityError
from .lund_suite import validate_lund2013_suite_manifest

_STATUS_MANIFEST = Path("validation/evidence-status-manifest.json")


class EvidenceState(str, Enum):
    """Public scientific evidence states in increasing empirical strength."""

    IMPLEMENTED = "implemented"
    INFRASTRUCTURE_VALIDATED = "infrastructure_validated"
    EMPIRICAL_EXECUTION_PENDING = "empirical_execution_pending"
    BOUNDED_EMPIRICAL_EVIDENCE = "bounded_empirical_evidence"
    REVIEWED_EMPIRICAL_EVIDENCE = "reviewed_empirical_evidence"
    FROZEN_EMPIRICAL_EVIDENCE = "frozen_empirical_evidence"


_STATE_LABELS = {
    EvidenceState.IMPLEMENTED: "Implemented",
    EvidenceState.INFRASTRUCTURE_VALIDATED: "Infrastructure validated",
    EvidenceState.EMPIRICAL_EXECUTION_PENDING: "Empirical execution pending",
    EvidenceState.BOUNDED_EMPIRICAL_EVIDENCE: "Bounded empirical evidence",
    EvidenceState.REVIEWED_EMPIRICAL_EVIDENCE: "Reviewed empirical evidence",
    EvidenceState.FROZEN_EMPIRICAL_EVIDENCE: "Frozen empirical evidence",
}


@dataclass(frozen=True, slots=True)
class EvidenceStatusRecord:
    """One public evidence-status record with explicit scientific boundaries."""

    dataset: str
    slug: str
    state: EvidenceState
    summary: str
    scope: str
    sampling_origin: str
    reference_strength: str
    blockers: tuple[str, ...]
    source_path: str | None
    fingerprint: str | None

    def to_dict(self) -> dict[str, Any]:
        """Return deterministic JSON-ready data."""
        payload = asdict(self)
        payload["state"] = self.state.value
        payload["blockers"] = list(self.blockers)
        return payload


@dataclass(frozen=True, slots=True)
class EvidenceStatusBundle:
    """Validated public evidence status generated from repository truth."""

    schema_version: int
    records: tuple[EvidenceStatusRecord, ...]
    manifest_fingerprint_sha256: str
    bundle_fingerprint_sha256: str

    def to_dict(self) -> dict[str, Any]:
        """Return deterministic machine-readable status data."""
        return {
            "schema_version": self.schema_version,
            "manifest_fingerprint_sha256": self.manifest_fingerprint_sha256,
            "records": [record.to_dict() for record in self.records],
            "bundle_fingerprint_sha256": self.bundle_fingerprint_sha256,
        }


def _git_blob_sha1(raw: bytes) -> str:
    header = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw, usedforsecurity=False).hexdigest()


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise BenchmarkIntegrityError(f"{label} is missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(f"{label} is not valid UTF-8 JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(f"{label} must be a JSON object: {path}")
    return payload


def _lookup(payload: dict[str, Any], dotted_path: str) -> Any:
    current: Any = payload
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise BenchmarkIntegrityError(
                f"Evidence record is missing required field {dotted_path!r}."
            )
        current = current[part]
    return current


def _safe_repository_path(root: Path, relative_text: str) -> Path:
    relative = Path(relative_text)
    if not relative.parts or relative.is_absolute() or ".." in relative.parts:
        raise BenchmarkIntegrityError("Evidence-status manifest contains an unsafe source path.")
    root_resolved = root.resolve()
    target = (root / relative).resolve()
    if target != root_resolved and root_resolved not in target.parents:
        raise BenchmarkIntegrityError("Evidence-status source path escapes the repository root.")
    return target


def _validate_manifest(manifest: dict[str, Any]) -> str:
    required = {"schema_version", "records", "manifest_fingerprint_sha256"}
    missing = sorted(required - set(manifest))
    if missing:
        raise BenchmarkIntegrityError(
            f"Evidence-status manifest is missing required fields: {missing}"
        )
    if manifest["schema_version"] != 1:
        raise BenchmarkIntegrityError("Unsupported evidence-status manifest schema version.")
    records = manifest["records"]
    if not isinstance(records, list) or not records:
        raise BenchmarkIntegrityError("Evidence-status manifest records must be a non-empty list.")

    claimed = manifest["manifest_fingerprint_sha256"]
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise BenchmarkIntegrityError("Evidence-status manifest fingerprint is missing or invalid.")
    body = {key: value for key, value in manifest.items() if key != "manifest_fingerprint_sha256"}
    observed = benchmark_fingerprint(body)
    if observed != claimed:
        raise BenchmarkIntegrityError("Evidence-status manifest fingerprint mismatch.")

    slugs: set[str] = set()
    for row in records:
        if not isinstance(row, dict):
            raise BenchmarkIntegrityError("Evidence-status manifest contains a non-object row.")
        slug = row.get("slug")
        if not isinstance(slug, str) or not slug or slug in slugs:
            raise BenchmarkIntegrityError("Evidence-status slugs must be unique and non-empty.")
        slugs.add(slug)
        try:
            EvidenceState(str(row["state"]))
        except (KeyError, ValueError) as exc:
            raise BenchmarkIntegrityError(
                f"Evidence-status record {slug!r} has an invalid state."
            ) from exc
        if not isinstance(row.get("blockers", []), list):
            raise BenchmarkIntegrityError(
                f"Evidence-status record {slug!r} blockers must be a list."
            )
        if not isinstance(row.get("required_equals", {}), dict):
            raise BenchmarkIntegrityError(
                f"Evidence-status record {slug!r} required_equals must be an object."
            )
    return claimed


def _validate_bound_source(root: Path, row: dict[str, Any]) -> dict[str, Any] | None:
    validator = str(row.get("validator", ""))
    if validator == "policy_only":
        if any(
            row.get(field) is not None
            for field in ("source_path", "git_blob_sha1", "fingerprint_field", "fingerprint")
        ):
            raise BenchmarkIntegrityError(
                f"Policy-only record {row['slug']!r} must not bind a source artifact."
            )
        return None

    relative_text = row.get("source_path")
    expected_blob = row.get("git_blob_sha1")
    fingerprint_field = row.get("fingerprint_field")
    expected_fingerprint = row.get("fingerprint")
    bound_values = (relative_text, expected_blob, fingerprint_field, expected_fingerprint)
    if not all(isinstance(value, str) and value for value in bound_values):
        raise BenchmarkIntegrityError(
            f"Evidence-status record {row['slug']!r} has an incomplete source binding."
        )

    source_path = _safe_repository_path(root, relative_text)
    if not source_path.is_file():
        raise BenchmarkIntegrityError(
            f"Evidence-status source is missing for {row['slug']!r}: {relative_text}"
        )
    raw = source_path.read_bytes()
    observed_blob = _git_blob_sha1(raw)
    if observed_blob != expected_blob:
        raise BenchmarkIntegrityError(
            f"Evidence-status source byte identity mismatch for {row['slug']!r}."
        )

    payload = _load_json_object(source_path, label=f"Evidence source for {row['slug']!r}")
    claimed_fingerprint = payload.get(fingerprint_field)
    if claimed_fingerprint != expected_fingerprint:
        raise BenchmarkIntegrityError(f"Evidence fingerprint mismatch for {row['slug']!r}.")

    required_equals = row.get("required_equals", {})
    for dotted_path, expected in required_equals.items():
        observed = _lookup(payload, str(dotted_path))
        if observed != expected:
            raise BenchmarkIntegrityError(
                f"Evidence semantic gate failed for {row['slug']!r}: "
                f"{dotted_path!r} expected {expected!r}, observed {observed!r}."
            )

    if validator == "lund2013_suite":
        validated = validate_lund2013_suite_manifest(source_path, verify_reports=True)
        if validated["suite_fingerprint_sha256"] != expected_fingerprint:
            raise BenchmarkIntegrityError("Lund2013 suite fingerprint does not match status policy.")
    elif validator == "benchmark_report":
        body = {
            key: value
            for key, value in payload.items()
            if key != "report_fingerprint_sha256"
        }
        if benchmark_fingerprint(body) != expected_fingerprint:
            raise BenchmarkIntegrityError(
                f"Benchmark report fingerprint recomputation failed for {row['slug']!r}."
            )
    elif validator == "semantic_lock":
        # Exact Git blob identity binds every byte for historical evidence records whose
        # fingerprint convention is record-specific. Scientific boundaries are checked above.
        pass
    else:
        raise BenchmarkIntegrityError(
            f"Unknown evidence-status validator {validator!r} for {row['slug']!r}."
        )
    return payload


def build_evidence_status(
    project_root: str | Path,
    *,
    manifest_path: str | Path | None = None,
) -> EvidenceStatusBundle:
    """Build a deterministic, fail-closed evidence-status bundle.

    Status is never inferred from metric direction or magnitude. It is promoted only when a
    versioned policy row binds exact evidence bytes, the declared fingerprint, and explicit
    scientific-boundary assertions.
    """
    root = Path(project_root)
    manifest_target = (
        _safe_repository_path(root, str(manifest_path))
        if manifest_path is not None
        else root / _STATUS_MANIFEST
    )
    manifest = _load_json_object(manifest_target, label="Evidence-status manifest")
    manifest_fingerprint = _validate_manifest(manifest)

    records: list[EvidenceStatusRecord] = []
    for row in manifest["records"]:
        _validate_bound_source(root, row)
        records.append(
            EvidenceStatusRecord(
                dataset=str(row["dataset"]),
                slug=str(row["slug"]),
                state=EvidenceState(str(row["state"])),
                summary=str(row["summary"]),
                scope=str(row["scope"]),
                sampling_origin=str(row["sampling_origin"]),
                reference_strength=str(row["reference_strength"]),
                blockers=tuple(str(item) for item in row.get("blockers", [])),
                source_path=(
                    str(row["source_path"]) if row.get("source_path") is not None else None
                ),
                fingerprint=(
                    str(row["fingerprint"]) if row.get("fingerprint") is not None else None
                ),
            )
        )

    records.sort(key=lambda item: item.slug)
    bundle_body = {
        "schema_version": 1,
        "manifest_fingerprint_sha256": manifest_fingerprint,
        "records": [record.to_dict() for record in records],
    }
    bundle_fingerprint = benchmark_fingerprint(bundle_body)
    return EvidenceStatusBundle(
        schema_version=1,
        records=tuple(records),
        manifest_fingerprint_sha256=manifest_fingerprint,
        bundle_fingerprint_sha256=bundle_fingerprint,
    )


def render_evidence_status_json(bundle: EvidenceStatusBundle) -> str:
    """Render deterministic machine-readable public evidence status."""
    return json.dumps(
        bundle.to_dict(),
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ) + "\n"


def render_evidence_status_markdown(bundle: EvidenceStatusBundle) -> str:
    """Render an accessible evidence-status table plus explicit scientific boundaries."""
    lines = [
        "# Evidence status",
        "",
        "This page is generated from versioned evidence policy and exact repository artifacts. "
        "Status is not inferred from whether a model metric looks favourable.",
        "",
        f"**Status bundle fingerprint:** `{bundle.bundle_fingerprint_sha256}`",
        "",
        "| Dataset / target | Status | Evidence scope | Sampling origin |",
        "| --- | --- | --- | --- |",
    ]
    for record in bundle.records:
        label = _STATE_LABELS[record.state]
        lines.append(
            f"| **{record.dataset}** | {label} | {record.scope} | {record.sampling_origin} |"
        )

    lines.extend(["", "## Dataset boundaries", ""])
    for record in bundle.records:
        lines.extend(
            [
                f"### {record.dataset}",
                "",
                f"**{_STATE_LABELS[record.state]}.** {record.summary}",
                "",
                f"- Reference strength: `{record.reference_strength}`",
            ]
        )
        if record.source_path:
            lines.append(f"- Versioned source: `{record.source_path}`")
        if record.fingerprint:
            lines.append(f"- Bound evidence fingerprint: `{record.fingerprint}`")
        if record.blockers:
            lines.append("- Open boundaries:")
            lines.extend(f"  - {item}" for item in record.blockers)
        else:
            lines.append("- Open boundaries: none recorded by the status policy.")
        lines.append("")

    lines.extend(
        [
            "## Interpretation rule",
            "",
            "A stronger status requires an explicit reviewed policy update plus integrity-valid "
            "evidence. Missing, malformed, byte-changed, fingerprint-mismatched, or scientifically "
            "incompatible evidence fails closed during site generation. Synthetic/demo outputs are "
            "never promoted into empirical evidence, derived 60 Hz remains distinct from native "
            "60 Hz/GP3 validation, and source-token-held-out designs remain distinct from "
            "participant-held-out designs.",
            "",
        ]
    )
    return "\n".join(lines)
