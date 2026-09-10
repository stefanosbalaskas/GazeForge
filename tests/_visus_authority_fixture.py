"""Synthetic authority-bound VISUS fixtures for fail-closed tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.visus_audit import VisusSourceAuditSpec, VisusSourceFileRecord
from gazeforge.visus_authoritative_source_common import (
    CERTIFICATE_RECORD_TYPE,
    CERTIFICATE_STATUS,
    SOURCE_RECHECK_FINGERPRINT,
    certificate_fingerprint,
)


def _write(root: Path, relative: str) -> tuple[str, int]:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"fixture:{relative}\n", encoding="utf-8")
    payload = path.read_bytes()
    return hashlib.sha256(payload).hexdigest(), len(payload)


def _record(
    root: Path,
    *,
    path: str,
    role: str,
    stimulus_id: str,
    participant_id: str | None = None,
    annotation_stream_id: str | None = None,
) -> VisusSourceFileRecord:
    digest, size = _write(root, path)
    return VisusSourceFileRecord(
        path=path,
        sha256=digest,
        bytes=size,
        role=role,
        stimulus_id=stimulus_id,
        participant_id=participant_id,
        annotation_stream_id=annotation_stream_id,
    )


def build_visus_authority_spec(
    root: Path,
    *,
    independent_streams: bool = False,
) -> VisusSourceAuditSpec:
    """Create a complete structural VISUS spec over deterministic synthetic files."""
    stimuli = [f"S{index:02d}" for index in range(1, 12)]
    records: list[VisusSourceFileRecord] = []
    for stimulus in stimuli:
        records.append(
            _record(
                root,
                path=f"video/{stimulus}.avi",
                role="video",
                stimulus_id=stimulus,
            )
        )
        records.append(
            _record(
                root,
                path=f"aoi/{stimulus}-annotator_a.xml",
                role="aoi_annotation",
                stimulus_id=stimulus,
                annotation_stream_id="annotator_a",
            )
        )
        if independent_streams:
            records.append(
                _record(
                    root,
                    path=f"aoi/{stimulus}-annotator_b.xml",
                    role="aoi_annotation",
                    stimulus_id=stimulus,
                    annotation_stream_id="annotator_b",
                )
            )
    for index in range(1, 26):
        participant = f"P{index:02d}"
        stimulus = stimuli[(index - 1) % len(stimuli)]
        records.append(
            _record(
                root,
                path=f"gaze/{participant}-{stimulus}.tsv",
                role="gaze",
                stimulus_id=stimulus,
                participant_id=participant,
            )
        )

    return VisusSourceAuditSpec(
        dataset_name="VISUS",
        dataset_version="authority-fixture",
        source="https://example.invalid/authoritative-visus",
        source_revision="fixture-revision",
        license="fixture-analysis-terms-v1",
        reuse_terms_source="https://example.invalid/authoritative-visus/terms",
        dataset_status="empirical",
        reuse_terms_verified=True,
        analysis_use_permitted=True,
        redistribution_status="prohibited",
        stimulus_mapping_verified=True,
        stimulus_mapping_basis="Synthetic exact fixture stimulus ledger.",
        participant_mapping_verified=True,
        participant_mapping_basis="Synthetic exact fixture participant ledger.",
        coordinate_unit="pixels",
        coordinate_unit_verified=True,
        coordinate_verification_basis="Synthetic fixture coordinate documentation.",
        timestamp_basis_verified=True,
        timestamp_verification_basis="Synthetic fixture frame-time documentation.",
        independent_annotation_streams_verified=independent_streams,
        independent_annotation_streams_basis=(
            "Synthetic fixture contains separately manifested independent streams."
            if independent_streams
            else ""
        ),
        files=records,
    )


def build_visus_authority_certificate(
    spec: VisusSourceAuditSpec,
) -> dict[str, object]:
    """Create a schema-valid reviewed certificate matching one synthetic spec."""
    inventory_rows = [
        {
            "path": record.path,
            "sha256": record.sha256,
            "bytes": int(record.bytes),
            "role": "other",
        }
        for record in sorted(spec.files, key=lambda item: item.path)
    ]
    certificate: dict[str, object] = {
        "record_type": CERTIFICATE_RECORD_TYPE,
        "status": CERTIFICATE_STATUS,
        "authoritative_source_recheck_fingerprint_sha256": SOURCE_RECHECK_FINGERPRINT,
        "candidate_fingerprint_sha256": "1" * 64,
        "review_fingerprint_sha256": "2" * 64,
        "source": {
            "artifact_sha256": "3" * 64,
            "source_reference": spec.source,
            "source_revision": spec.source_revision,
            "source_authority_claim": "author_hosted_distribution",
        },
        "rights": {
            "evidence_sha256": "4" * 64,
            "evidence_reference": spec.reuse_terms_source,
            "license_or_terms_identifier": spec.license,
            "analysis_use_permitted": True,
            "redistribution_status": spec.redistribution_status,
            "rights_scope_verified": True,
            "raw_source_redistribution_action_authorized": False,
            "raw_rights_text_copied_to_certificate": False,
        },
        "inventory": {
            "file_count": len(spec.files),
            "fingerprint_sha256": benchmark_fingerprint(inventory_rows),
            "published_participant_count": 25,
            "published_stimulus_count": 11,
        },
        "authority_boundary": {
            "source_authority_verified": True,
            "current_authoritative_distribution_identity_verified": True,
            "source_artifact_matches_authoritative_distribution_verified": True,
            "extracted_tree_matches_source_artifact_verified": True,
            "source_audit_stage_authorized": True,
        },
        "scientific_boundary": {
            "dataset_status_empirical_created": False,
            "participant_mapping_verified": False,
            "stimulus_mapping_verified": False,
            "coordinate_basis_verified": False,
            "timestamp_basis_verified": False,
            "independent_annotation_streams_verified": False,
            "human_human_agreement_created": False,
            "model_human_validation_created": False,
            "frozen_evidence_created": False,
            "raw_source_redistribution_action_authorized": False,
        },
    }
    certificate["certificate_fingerprint_sha256"] = certificate_fingerprint(certificate)
    return certificate


def write_visus_authority_certificate(
    path: Path,
    certificate: dict[str, object],
) -> Path:
    """Write a deterministic authority-certificate fixture."""
    path.write_text(
        json.dumps(certificate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path
