import hashlib
from pathlib import Path

import pandas as pd
import pytest

from gazeforge.dynamic_aoi import DynamicAOIKeyframe
from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.visus_agreement import run_visus_dynamic_aoi_human_agreement
from gazeforge.visus_audit import (
    VisusSourceAuditSpec,
    VisusSourceFileRecord,
    audit_visus_source,
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


def _audit(root: Path, *, independent: bool = True):
    stimuli = [f"S{index:02d}" for index in range(1, 12)]
    files: list[VisusSourceFileRecord] = []
    for stimulus in stimuli:
        files.append(
            _record(
                root,
                path=f"video/{stimulus}.avi",
                role="video",
                stimulus_id=stimulus,
            )
        )
        for stream in ("annotator_a", "annotator_b"):
            files.append(
                _record(
                    root,
                    path=f"aoi/{stimulus}-{stream}.xml",
                    role="aoi_annotation",
                    stimulus_id=stimulus,
                    annotation_stream_id=stream,
                )
            )
    for index in range(1, 26):
        participant = f"P{index:02d}"
        stimulus = stimuli[(index - 1) % len(stimuli)]
        files.append(
            _record(
                root,
                path=f"gaze/{participant}-{stimulus}.tsv",
                role="gaze",
                stimulus_id=stimulus,
                participant_id=participant,
            )
        )

    spec = VisusSourceAuditSpec(
        dataset_name="VISUS",
        dataset_version="agreement-fixture",
        source="https://example.invalid/visus",
        source_revision="fixture-snapshot",
        license="Reviewed fixture terms.",
        reuse_terms_source="https://example.invalid/terms",
        dataset_status="empirical",
        reuse_terms_verified=True,
        analysis_use_permitted=True,
        redistribution_status="restricted",
        stimulus_mapping_verified=True,
        stimulus_mapping_basis="Fixture stimulus manifest.",
        participant_mapping_verified=True,
        participant_mapping_basis="Fixture participant manifest.",
        coordinate_unit="pixels",
        coordinate_unit_verified=True,
        coordinate_verification_basis="Fixture coordinate documentation.",
        timestamp_basis_verified=True,
        timestamp_verification_basis="Fixture video frame-time documentation.",
        independent_annotation_streams_verified=independent,
        independent_annotation_streams_basis=(
            "Fixture streams created independently for agreement testing." if independent else ""
        ),
        files=files,
    )
    return audit_visus_source(root, spec)


def _inputs():
    stimuli = [f"S{index:02d}" for index in range(1, 12)]
    left = {}
    right = {}
    timestamps = {}
    fixations = {}
    for index, stimulus in enumerate(stimuli):
        shift = float(index)
        common_left = [
            DynamicAOIKeyframe("left-target", "person", 0.0, shift, 0.0, 100.0 + shift, 100.0),
            DynamicAOIKeyframe(
                "left-target",
                "person",
                100.0,
                20.0 + shift,
                0.0,
                120.0 + shift,
                100.0,
            ),
        ]
        common_right = [
            DynamicAOIKeyframe(
                "right-target", "person", 0.0, shift, 0.0, 100.0 + shift, 100.0
            ),
            DynamicAOIKeyframe(
                "right-target",
                "person",
                100.0,
                20.0 + shift,
                0.0,
                120.0 + shift,
                100.0,
            ),
        ]
        if stimulus == "S01":
            common_left.extend(
                [
                    DynamicAOIKeyframe("left-extra", "vehicle", 0.0, 300.0, 300.0, 350.0, 350.0),
                    DynamicAOIKeyframe(
                        "left-extra", "vehicle", 100.0, 300.0, 300.0, 350.0, 350.0
                    ),
                ]
            )
        left[stimulus] = common_left
        right[stimulus] = common_right
        timestamps[stimulus] = [0.0, 50.0, 100.0]
        fixations[stimulus] = pd.DataFrame(
            {
                "timestamp_ms": [0.0, 50.0, 100.0],
                "x_px": [20.0 + shift, 30.0 + shift, 40.0 + shift],
                "y_px": [20.0, 20.0, 20.0],
            }
        )
    return left, right, timestamps, fixations


def test_visus_human_agreement_is_bidirectional_and_fingerprinted(tmp_path):
    audit = _audit(tmp_path)
    left, right, timestamps, fixations = _inputs()
    run = run_visus_dynamic_aoi_human_agreement(
        audit,
        left_by_stimulus=left,
        right_by_stimulus=right,
        timestamps_by_stimulus=timestamps,
        fixations_by_stimulus=fixations,
        left_stream_id="annotator_a",
        right_stream_id="annotator_b",
        timestamp_grid_basis="fixture video frame timestamps",
        max_interpolation_gap_ms=100.0,
        include_matches=True,
    )

    assert set(run.directional_summary["direction"]) == {"left_to_right", "right_to_left"}
    assert len(run.per_stimulus) == 22
    assert len(run.per_timestamp) == 66
    left_to_right = run.directional_summary.set_index("direction").loc["left_to_right"]
    right_to_left = run.directional_summary.set_index("direction").loc["right_to_left"]
    assert left_to_right["precision"] < left_to_right["recall"]
    assert right_to_left["recall"] < right_to_left["precision"]
    assert run.fixation_assignment is not None
    assert run.fixation_assignment["exact_agreement"] == pytest.approx(1.0)
    assert run.report["benchmark"]["human_annotator_count"] == 2
    assert run.report["protocol"]["independent_annotation_streams_verified"] is True
    assert run.report["protocol"]["human_agreement_reference_not_ground_truth"] is True
    assert len(run.report["protocol"]["input_fingerprints"]) == 11
    assert len(run.report["report_fingerprint_sha256"]) == 64


def test_visus_human_agreement_is_blocked_without_verified_independent_streams(tmp_path):
    audit = _audit(tmp_path, independent=False)
    left, right, timestamps, _ = _inputs()
    with pytest.raises(BenchmarkIntegrityError, match="blocked"):
        run_visus_dynamic_aoi_human_agreement(
            audit,
            left_by_stimulus=left,
            right_by_stimulus=right,
            timestamps_by_stimulus=timestamps,
            left_stream_id="annotator_a",
            right_stream_id="annotator_b",
            timestamp_grid_basis="fixture video frame timestamps",
            max_interpolation_gap_ms=100.0,
        )


def test_visus_human_agreement_requires_distinct_streams(tmp_path):
    audit = _audit(tmp_path)
    left, _, timestamps, _ = _inputs()
    with pytest.raises(ValueError, match="distinct"):
        run_visus_dynamic_aoi_human_agreement(
            audit,
            left_by_stimulus=left,
            right_by_stimulus=left,
            timestamps_by_stimulus=timestamps,
            left_stream_id="annotator_a",
            right_stream_id="annotator_a",
            timestamp_grid_basis="fixture video frame timestamps",
            max_interpolation_gap_ms=100.0,
        )


def test_visus_human_agreement_revalidates_source_fingerprint(tmp_path):
    audit = _audit(tmp_path)
    left, right, timestamps, _ = _inputs()
    audit.report["identity"]["participant_count"] = 999
    with pytest.raises(BenchmarkIntegrityError, match="fingerprint"):
        run_visus_dynamic_aoi_human_agreement(
            audit,
            left_by_stimulus=left,
            right_by_stimulus=right,
            timestamps_by_stimulus=timestamps,
            left_stream_id="annotator_a",
            right_stream_id="annotator_b",
            timestamp_grid_basis="fixture video frame timestamps",
            max_interpolation_gap_ms=100.0,
        )
