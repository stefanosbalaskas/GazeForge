import numpy as np
import pandas as pd
import pytest

from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError, SchemaError
from gazeforge.gaze_in_wild_agreement import run_gaze_in_wild_labeller_agreement
from gazeforge.gaze_in_wild_audit import (
    GazeInWildAuditedFile,
    GazeInWildLabelFileRecord,
    GazeInWildProcessFileRecord,
    GazeInWildSourceAuditRun,
    GazeInWildSourceAuditSpec,
)
from gazeforge.schema import GazeFrame


def _spec() -> GazeInWildSourceAuditSpec:
    process_files = [
        GazeInWildProcessFileRecord(path="P01_T01.mat", sha256="a" * 64, bytes=1),
        GazeInWildProcessFileRecord(path="P02_T02.mat", sha256="b" * 64, bytes=1),
    ]
    label_files = []
    hashes = iter("cdef")
    for participant, trial in (("P01", "T01"), ("P02", "T02")):
        process_path = f"{participant}_{trial}.mat"
        for labeller in (1, 2):
            label_files.append(
                GazeInWildLabelFileRecord(
                    path=f"{participant}_{trial}_Lbr_{labeller}.mat",
                    sha256=next(hashes) * 64,
                    bytes=1,
                    participant_id=participant,
                    trial_id=trial,
                    labeller_id=labeller,
                    process_path=process_path,
                )
            )
    return GazeInWildSourceAuditSpec(
        dataset_name="Gaze-in-the-Wild",
        dataset_version="test-snapshot",
        source="https://example.invalid/gaze-in-wild",
        source_revision="snapshot-1",
        license="Verified fixture terms.",
        reuse_terms_source="https://example.invalid/terms",
        dataset_status="empirical",
        reuse_terms_verified=True,
        analysis_use_permitted=True,
        redistribution_status="restricted",
        participant_mapping_verified=True,
        participant_mapping_basis="Fixture participant/trial mapping.",
        coordinate_unit="pixels",
        coordinate_unit_verified=True,
        coordinate_verification_basis="Fixture POR coordinates are pixels.",
        pixel_kinematics_compatible=True,
        label_files=label_files,
        process_files=process_files,
    )


def _frame(
    participant: str,
    trial: str,
    labeller: int,
    rate_hz: float,
) -> GazeFrame:
    labels_left = [
        "fixation",
        "fixation",
        "saccade",
        "saccade",
        "pursuit",
        "pursuit",
        "unlabelled",
        "fixation",
        "fixation",
        "saccade",
    ]
    labels_right = [
        "fixation",
        "fixation",
        "saccade",
        "pursuit",
        "pursuit",
        "pursuit",
        "unlabelled",
        "fixation",
        "saccade",
        "saccade",
    ]
    labels = labels_left if labeller == 1 else labels_right
    n = len(labels)
    valid = np.ones(n, dtype=bool)
    valid[6] = False
    confidence = np.ones(n, dtype=float)
    confidence[6] = 0.1
    data = pd.DataFrame(
        {
            "participant_id": participant,
            "trial_id": trial,
            "timestamp_ms": np.arange(n, dtype=float) * (1000.0 / rate_hz),
            "x_px": np.arange(n, dtype=float) + 100.0,
            "y_px": np.arange(n, dtype=float) + 200.0,
            "validity": valid,
            "confidence": confidence,
            "event_label": labels,
            "annotator": f"labeller_{labeller}",
            "dataset_id": "Gaze-in-the-Wild",
        }
    )
    return GazeFrame(data=data, sampling_rate_hz=rate_hz, metadata={})


def _audit() -> GazeInWildSourceAuditRun:
    spec = _spec()
    by_identity = {
        (record.participant_id, record.trial_id, record.labeller_id): record
        for record in spec.label_files
    }
    files = []
    for participant, trial, rate in (("P01", "T01", 120.0), ("P02", "T02", 100.0)):
        for labeller in (1, 2):
            record = by_identity[(participant, trial, labeller)]
            files.append(
                GazeInWildAuditedFile(
                    record=record,
                    gaze=_frame(participant, trial, labeller, rate),
                )
            )

    spec_fingerprint = benchmark_fingerprint(spec.to_dict())
    body = {
        "status": "verified",
        "spec_fingerprint_sha256": spec_fingerprint,
        "identity": {"labeller_count": 2},
        "label_inventory": {"manifest_fingerprint_sha256": "1" * 64},
        "process_inventory": {"manifest_fingerprint_sha256": "2" * 64},
    }
    report_fingerprint = benchmark_fingerprint(body)
    report = {**body, "report_fingerprint_sha256": report_fingerprint}
    for item in files:
        item.gaze.metadata.update(
            {
                "source_audit_status": "verified",
                "source_audit_report_fingerprint_sha256": report_fingerprint,
                "source_audit_spec_fingerprint_sha256": spec_fingerprint,
            }
        )
    return GazeInWildSourceAuditRun(spec=spec, files=files, report=report)


def test_gaze_in_wild_labeller_agreement_is_rate_aware_and_bidirectional():
    run = run_gaze_in_wild_labeller_agreement(
        _audit(),
        left_labeller=1,
        right_labeller=2,
    )

    assert set(run.per_trial["sampling_rate_hz"]) == {100.0, 120.0}
    assert run.report["benchmark"]["sampling_rates_hz"] == [100.0, 120.0]
    assert run.report["benchmark"]["sampling_origin"] == "native"
    assert run.report["protocol"]["resampling"] is None
    assert run.report["protocol"]["underlying_gaze_identity_reverified"] is True
    assert run.report["metrics"]["sample_agreement_all_labels"]["exact_agreement"] < 1.0
    assert run.report["metrics"]["sample_agreement_analysis_labels"][
        "n_excluded_pairwise_samples"
    ] == 2
    assert 0.0 <= run.left_reference_events.summary["f1"] <= 1.0
    assert 0.0 <= run.right_reference_events.summary["f1"] <= 1.0
    assert len(run.report["report_fingerprint_sha256"]) == 64


def test_gaze_in_wild_labeller_agreement_requires_complete_overlap_by_default():
    audit = _audit()
    audit.files = [
        item
        for item in audit.files
        if not (
            item.record.participant_id == "P02"
            and item.record.trial_id == "T02"
            and item.record.labeller_id == 2
        )
    ]
    with pytest.raises(SchemaError, match="Complete labeller overlap"):
        run_gaze_in_wild_labeller_agreement(
            audit,
            left_labeller=1,
            right_labeller=2,
        )

    run = run_gaze_in_wild_labeller_agreement(
        audit,
        left_labeller=1,
        right_labeller=2,
        require_complete_overlap=False,
    )
    assert run.report["protocol"]["shared_trial_count"] == 1
    assert run.report["protocol"]["left_only_trials"] == [["P02", "T02"]]


def test_gaze_in_wild_labeller_agreement_rechecks_underlying_gaze_identity():
    audit = _audit()
    target = next(
        item
        for item in audit.files
        if item.record.participant_id == "P01" and item.record.labeller_id == 2
    )
    target.gaze.data.loc[3, "x_px"] += 1.0

    with pytest.raises(SchemaError, match="identical underlying gaze"):
        run_gaze_in_wild_labeller_agreement(
            audit,
            left_labeller=1,
            right_labeller=2,
        )


def test_gaze_in_wild_labeller_agreement_revalidates_source_audit_fingerprint():
    audit = _audit()
    audit.report["report_fingerprint_sha256"] = "0" * 64

    with pytest.raises(BenchmarkIntegrityError, match="fingerprint"):
        run_gaze_in_wild_labeller_agreement(
            audit,
            left_labeller=1,
            right_labeller=2,
        )


def test_gaze_in_wild_labeller_agreement_requires_distinct_labellers():
    with pytest.raises(ValueError, match="distinct labellers"):
        run_gaze_in_wild_labeller_agreement(
            _audit(),
            left_labeller=1,
            right_labeller=1,
        )
