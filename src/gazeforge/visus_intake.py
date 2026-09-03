"""Audited canonical AOI intake for VISUS without guessing the raw XML schema."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

from .benchmarks import benchmark_fingerprint
from .dynamic_aoi import DynamicAOIKeyframe
from .exceptions import BenchmarkIntegrityError, SchemaError
from .provenance import fingerprint_frame
from .visus_audit import VisusSourceAuditRun

_REQUIRED_COLUMNS = (
    "source_path",
    "stimulus_id",
    "annotation_stream_id",
    "frame_index",
    "aoi_id",
    "label",
    "xmin",
    "ymin",
    "xmax",
    "ymax",
)


@dataclass(slots=True)
class VisusCanonicalAOIIntakeRun:
    """Canonical VISUS AOIs linked back to an exact audited source snapshot."""

    canonical: pd.DataFrame
    by_stream: dict[str, dict[str, list[DynamicAOIKeyframe]]]
    report: dict[str, Any]


def _resolved(value: str) -> bool:
    text = str(value).strip()
    upper = text.upper()
    return bool(text) and "REPLACE" not in upper and "VERIFY" not in upper


def _verify_audit_integrity(audit: VisusSourceAuditRun) -> None:
    if not isinstance(audit, VisusSourceAuditRun):
        raise TypeError("audit must be a VisusSourceAuditRun instance.")
    if audit.report.get("status") != "verified":
        raise BenchmarkIntegrityError("VISUS source audit is not verified.")

    report_fingerprint = str(audit.report.get("report_fingerprint_sha256", ""))
    report_body = {
        key: value
        for key, value in audit.report.items()
        if key != "report_fingerprint_sha256"
    }
    if len(report_fingerprint) != 64 or benchmark_fingerprint(report_body) != report_fingerprint:
        raise BenchmarkIntegrityError("VISUS source-audit report fingerprint does not revalidate.")

    spec_fingerprint = str(audit.report.get("spec_fingerprint_sha256", ""))
    if benchmark_fingerprint(audit.spec.to_dict()) != spec_fingerprint:
        raise BenchmarkIntegrityError(
            "VISUS source-audit specification fingerprint does not revalidate."
        )

    manifest_rows = [asdict(item.record) for item in audit.files]
    expected_manifest = str(
        audit.report.get("inventory", {}).get("manifest_fingerprint_sha256", "")
    )
    if benchmark_fingerprint(manifest_rows) != expected_manifest:
        raise BenchmarkIntegrityError("VISUS source manifest fingerprint does not revalidate.")


def _annotation_manifest(audit: VisusSourceAuditRun) -> dict[str, Any]:
    records = {
        item.record.path: item.record
        for item in audit.files
        if item.record.role == "aoi_annotation"
    }
    if not records:
        raise BenchmarkIntegrityError("VISUS source audit contains no AOI annotation files.")
    return records


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    values = pd.to_numeric(frame[column], errors="coerce")
    if not np.isfinite(values.to_numpy(dtype=float)).all():
        raise SchemaError(f"VISUS canonical AOI column {column!r} must be finite numeric data.")
    return values.astype(float)


def _validate_rows(
    table: pd.DataFrame,
    *,
    manifest: Mapping[str, Any],
    frame_index_base: int,
    video_rate_hz: float,
    coordinate_unit: str,
    video_resolution_px: tuple[int, int],
    require_complete_manifest_coverage: bool,
) -> pd.DataFrame:
    missing = [column for column in _REQUIRED_COLUMNS if column not in table.columns]
    if missing:
        raise SchemaError(f"VISUS canonical AOI table is missing columns: {missing}")
    if table.empty:
        raise SchemaError("VISUS canonical AOI table cannot be empty.")

    selected_columns = list(_REQUIRED_COLUMNS)
    if "confidence" in table:
        selected_columns.append("confidence")
    canonical = table.loc[:, selected_columns].copy()
    for column in ("source_path", "stimulus_id", "annotation_stream_id", "aoi_id", "label"):
        canonical[column] = canonical[column].astype(str).str.strip()
        if (canonical[column] == "").any():
            raise SchemaError(f"VISUS canonical AOI column {column!r} cannot contain empty values.")

    frame_values = _numeric(canonical, "frame_index")
    rounded = np.rint(frame_values.to_numpy(dtype=float))
    if not np.allclose(frame_values.to_numpy(dtype=float), rounded, rtol=0.0, atol=1e-9):
        raise SchemaError("VISUS frame_index values must be integers.")
    canonical["frame_index"] = rounded.astype(int)
    if (canonical["frame_index"] < frame_index_base).any():
        raise SchemaError(
            f"VISUS frame_index values must be >= the explicit base {frame_index_base}."
        )

    for column in ("xmin", "ymin", "xmax", "ymax"):
        canonical[column] = _numeric(canonical, column)
    if (canonical["xmax"] <= canonical["xmin"]).any() or (
        canonical["ymax"] <= canonical["ymin"]
    ).any():
        raise SchemaError("VISUS AOI boxes must satisfy xmax > xmin and ymax > ymin.")

    if "confidence" not in canonical:
        canonical["confidence"] = 1.0
    else:
        canonical["confidence"] = _numeric(canonical, "confidence")
    if ((canonical["confidence"] < 0.0) | (canonical["confidence"] > 1.0)).any():
        raise SchemaError("VISUS AOI confidence must lie in [0, 1].")

    if coordinate_unit in {"pixel", "pixels", "px"}:
        width, height = video_resolution_px
        outside = (
            (canonical["xmin"] < 0.0)
            | (canonical["ymin"] < 0.0)
            | (canonical["xmax"] > float(width))
            | (canonical["ymax"] > float(height))
        )
        if outside.any():
            raise SchemaError(
                "VISUS pixel AOI bounds must remain inside the audited video resolution."
            )

    for row in canonical.itertuples(index=False):
        record = manifest.get(row.source_path)
        if record is None:
            raise SchemaError(
                f"VISUS canonical AOI source_path is not an audited AOI file: {row.source_path!r}."
            )
        if str(record.stimulus_id) != row.stimulus_id:
            raise SchemaError(
                f"VISUS canonical AOI stimulus_id does not match manifest path {row.source_path!r}."
            )
        if str(record.annotation_stream_id) != row.annotation_stream_id:
            raise SchemaError(
                "VISUS canonical AOI annotation_stream_id does not match its audited source file."
            )

    if require_complete_manifest_coverage:
        observed_paths = set(canonical["source_path"].tolist())
        missing_paths = sorted(set(manifest) - observed_paths)
        extra_paths = sorted(observed_paths - set(manifest))
        if missing_paths or extra_paths:
            raise SchemaError(
                "VISUS canonical AOI extraction must cover every audited AOI annotation file: "
                f"missing={missing_paths}, extra={extra_paths}."
            )

    duplicate_key = ["stimulus_id", "annotation_stream_id", "aoi_id", "frame_index"]
    if canonical.duplicated(duplicate_key).any():
        raise SchemaError(
            "VISUS canonical AOI table contains duplicate stimulus/stream/AOI/frame identities."
        )

    label_counts = canonical.groupby(
        ["stimulus_id", "annotation_stream_id", "aoi_id"], dropna=False
    )["label"].nunique()
    if (label_counts > 1).any():
        raise SchemaError("Each VISUS AOI track must keep one semantic label across keyframes.")

    canonical["timestamp_ms"] = (
        canonical["frame_index"].astype(float) - float(frame_index_base)
    ) * (1000.0 / float(video_rate_hz))
    canonical["source"] = "human-manual"
    canonical = canonical.sort_values(
        ["annotation_stream_id", "stimulus_id", "aoi_id", "frame_index", "source_path"],
        kind="stable",
    ).reset_index(drop=True)
    return canonical


def _to_keyframes(canonical: pd.DataFrame) -> dict[str, dict[str, list[DynamicAOIKeyframe]]]:
    result: dict[str, dict[str, list[DynamicAOIKeyframe]]] = {}
    grouped = canonical.groupby(["annotation_stream_id", "stimulus_id"], sort=True)
    for (stream_id, stimulus_id), subset in grouped:
        frames = [
            DynamicAOIKeyframe(
                aoi_id=str(row.aoi_id),
                label=str(row.label),
                timestamp_ms=float(row.timestamp_ms),
                xmin=float(row.xmin),
                ymin=float(row.ymin),
                xmax=float(row.xmax),
                ymax=float(row.ymax),
                confidence=float(row.confidence),
                source="human-manual",
            )
            for row in subset.itertuples(index=False)
        ]
        result.setdefault(str(stream_id), {})[str(stimulus_id)] = frames
    return result


def prepare_visus_canonical_aoi_intake(
    audit: VisusSourceAuditRun,
    table: pd.DataFrame,
    *,
    extraction_basis: str,
    frame_index_base: int,
    require_complete_manifest_coverage: bool = True,
) -> VisusCanonicalAOIIntakeRun:
    """Validate a reviewed VISUS AOI extraction and convert frames to canonical keyframes.

    This function deliberately does not parse ViPER XML. It accepts a separately extracted,
    reviewable table and requires every row to link to the exact AOI XML file already verified by
    ``VisusSourceAuditRun``. Frame-to-time conversion uses the audited published video frame rate
    and an explicit 0- or 1-based frame convention supplied by the caller.
    """
    _verify_audit_integrity(audit)
    if not isinstance(table, pd.DataFrame):
        raise TypeError("table must be a pandas DataFrame.")
    if not _resolved(extraction_basis):
        raise ValueError("extraction_basis must describe how the canonical table was obtained.")
    if int(frame_index_base) not in {0, 1}:
        raise ValueError("frame_index_base must be explicitly 0 or 1.")
    if not audit.spec.timestamp_basis_verified:
        raise BenchmarkIntegrityError(
            "VISUS canonical intake requires an audited timestamp/frame-time basis."
        )
    if not audit.spec.coordinate_unit_verified:
        raise BenchmarkIntegrityError("VISUS canonical intake requires audited coordinate units.")

    video_rate_hz = float(audit.spec.published_video_frame_rate_hz)
    if not np.isfinite(video_rate_hz) or video_rate_hz <= 0:
        raise BenchmarkIntegrityError("VISUS audited video frame rate must be finite and positive.")
    manifest = _annotation_manifest(audit)
    input_fingerprint = fingerprint_frame(table)
    coordinate_unit = str(audit.spec.coordinate_unit).strip().lower()
    canonical = _validate_rows(
        table,
        manifest=manifest,
        frame_index_base=int(frame_index_base),
        video_rate_hz=video_rate_hz,
        coordinate_unit=coordinate_unit,
        video_resolution_px=audit.spec.published_video_resolution_px,
        require_complete_manifest_coverage=bool(require_complete_manifest_coverage),
    )
    by_stream = _to_keyframes(canonical)

    source_rows = []
    for path in sorted(set(canonical["source_path"].tolist())):
        record = manifest[path]
        source_rows.append(
            {
                "path": record.path,
                "sha256": record.sha256,
                "bytes": int(record.bytes),
                "stimulus_id": record.stimulus_id,
                "annotation_stream_id": record.annotation_stream_id,
            }
        )

    body = {
        "status": "verified-canonical-intake",
        "dataset": "VISUS",
        "source_audit_report_fingerprint_sha256": audit.report["report_fingerprint_sha256"],
        "source_audit_spec_fingerprint_sha256": audit.report["spec_fingerprint_sha256"],
        "source_manifest_fingerprint_sha256": audit.report["inventory"][
            "manifest_fingerprint_sha256"
        ],
        "input_table_fingerprint_sha256": input_fingerprint,
        "canonical_table_fingerprint_sha256": fingerprint_frame(canonical),
        "extraction_basis": str(extraction_basis).strip(),
        "frame_index_base": int(frame_index_base),
        "video_frame_rate_hz": video_rate_hz,
        "frame_to_timestamp_formula": (
            "(frame_index - frame_index_base) * 1000 / video_frame_rate_hz"
        ),
        "coordinate_unit": audit.spec.coordinate_unit,
        "video_resolution_px": list(audit.spec.published_video_resolution_px),
        "complete_annotation_manifest_coverage_required": bool(
            require_complete_manifest_coverage
        ),
        "row_count": int(len(canonical)),
        "stimulus_ids": sorted(canonical["stimulus_id"].unique().tolist()),
        "annotation_stream_ids": sorted(canonical["annotation_stream_id"].unique().tolist()),
        "aoi_source_files": source_rows,
        "claim_limits": [
            "Canonical intake verifies linkage and table invariants, not raw ViPER XML parsing.",
            "No model-performance or human-agreement claim is created by this intake step.",
            (
                "Human-human agreement remains conditional on independently verified "
                "annotation streams."
            ),
        ],
    }
    report = {**body, "report_fingerprint_sha256": benchmark_fingerprint(body)}
    return VisusCanonicalAOIIntakeRun(
        canonical=canonical,
        by_stream=by_stream,
        report=report,
    )
