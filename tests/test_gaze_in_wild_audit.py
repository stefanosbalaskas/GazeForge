import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from scipy.io import savemat

from gazeforge.exceptions import SchemaError
from gazeforge.gaze_in_wild_audit import (
    GazeInWildLabelFileRecord,
    GazeInWildProcessFileRecord,
    GazeInWildSourceAuditSpec,
    audit_gaze_in_wild_source,
    audited_gaze_in_wild_files_by_labeller,
    load_gaze_in_wild_source_audit_spec,
)


def _write_process(path: Path, n: int = 8) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sample = np.arange(n, dtype=float)
    por = np.vstack(
        [
            0.25 + sample * 0.01,
            0.40 + sample * 0.01,
        ]
    )
    confidence = np.linspace(1.0, 0.65, n)
    savemat(
        path,
        {
            "ProcessData": {
                "ETG": {
                    "POR": por,
                    "Confidence": confidence,
                    "SceneResolution": np.array([1920, 1080], dtype=float),
                }
            }
        },
    )


def _write_label(
    path: Path,
    *,
    labeller: int,
    rate_hz: float = 120.0,
    n: int = 8,
    time_offset_s: float = 0.0,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    labels = np.resize(np.array([1, 1, 3, 3, 2, 2, 4, 5], dtype=int), n)
    times = time_offset_s + np.arange(n, dtype=float) / rate_hz
    savemat(path, {"LabelData": {"T": times, "Labels": labels, "LbrIdx": labeller}})


def _digest_record(path: Path) -> tuple[str, int]:
    payload = path.read_bytes()
    return hashlib.sha256(payload).hexdigest(), len(payload)


def _process_record(root: Path, relative: str) -> GazeInWildProcessFileRecord:
    digest, size = _digest_record(root / relative)
    return GazeInWildProcessFileRecord(path=relative, sha256=digest, bytes=size)


def _label_record(
    root: Path,
    relative: str,
    *,
    participant: str,
    trial: str,
    labeller: int,
    process_path: str,
) -> GazeInWildLabelFileRecord:
    digest, size = _digest_record(root / relative)
    return GazeInWildLabelFileRecord(
        path=relative,
        sha256=digest,
        bytes=size,
        participant_id=participant,
        trial_id=trial,
        labeller_id=labeller,
        process_path=process_path,
    )


def _fixture(root: Path) -> tuple[Path, Path, GazeInWildSourceAuditSpec]:
    label_root = root / "LabelData"
    process_root = root / "ProcessData"

    _write_process(process_root / "P01_task.mat")
    _write_process(process_root / "P02_task.mat")
    for labeller in (1, 2):
        _write_label(label_root / f"P01_task_Lbr_{labeller}.mat", labeller=labeller)
        _write_label(
            label_root / f"P02_task_Lbr_{labeller}.mat",
            labeller=labeller,
            rate_hz=100.0,
        )

    process_files = [
        _process_record(process_root, "P01_task.mat"),
        _process_record(process_root, "P02_task.mat"),
    ]
    label_files = []
    for participant in ("P01", "P02"):
        for labeller in (1, 2):
            label_files.append(
                _label_record(
                    label_root,
                    f"{participant}_task_Lbr_{labeller}.mat",
                    participant=participant,
                    trial="task",
                    labeller=labeller,
                    process_path=f"{participant}_task.mat",
                )
            )

    spec = GazeInWildSourceAuditSpec(
        dataset_name="Gaze-in-the-Wild",
        dataset_version="test-snapshot",
        source="https://example.invalid/gaze-in-wild",
        source_revision="snapshot-abc123",
        license="Verified research-use terms for this fixture.",
        reuse_terms_source="https://example.invalid/terms",
        dataset_status="empirical",
        reuse_terms_verified=True,
        analysis_use_permitted=True,
        redistribution_status="restricted",
        participant_mapping_verified=True,
        participant_mapping_basis="Fixture filename-to-participant/task manifest.",
        coordinate_unit="pixels",
        coordinate_unit_verified=True,
        coordinate_verification_basis=(
            "Fixture uses official normalized ProcessData.ETG.POR plus SceneResolution and "
            "loads to canonical pixels."
        ),
        pixel_kinematics_compatible=True,
        label_files=label_files,
        process_files=process_files,
    )
    return label_root, process_root, spec


def test_gaze_in_wild_source_audit_verifies_inventory_rates_and_labeller_gaze(tmp_path):
    label_root, process_root, spec = _fixture(tmp_path)
    run = audit_gaze_in_wild_source(label_root, process_root, spec)

    assert run.report["status"] == "verified"
    assert run.report["label_inventory"]["file_count"] == 4
    assert run.report["process_inventory"]["file_count"] == 2
    assert run.report["identity"]["participant_count"] == 2
    assert run.report["identity"]["labeller_count"] == 2
    assert run.report["identity"]["multi_labeller_trial_count"] == 2
    assert run.report["sampling"]["min_observed_sampling_rate_hz"] == pytest.approx(100.0)
    assert run.report["sampling"]["max_observed_sampling_rate_hz"] == pytest.approx(120.0)
    assert len(run.report["report_fingerprint_sha256"]) == 64
    assert len(run.files) == 4
    for item in run.files:
        assert item.gaze.metadata["source_audit_status"] == "verified"
        assert item.gaze.metadata["coordinate_unit_verified"] is True
        assert item.gaze.metadata["redistribution_status"] == "restricted"
        assert len(item.gaze.metadata["source_audit_report_fingerprint_sha256"]) == 64


def test_audited_files_group_by_labeller_without_hiding_per_file_rates(tmp_path):
    label_root, process_root, spec = _fixture(tmp_path)
    grouped = audited_gaze_in_wild_files_by_labeller(
        audit_gaze_in_wild_source(label_root, process_root, spec)
    )

    assert set(grouped) == {1, 2}
    assert [item.record.participant_id for item in grouped[1]] == ["P01", "P02"]
    assert {item.gaze.sampling_rate_hz for item in grouped[1]} == {100.0, 120.0}


def test_gaze_in_wild_source_audit_rejects_tampered_label_file(tmp_path):
    label_root, process_root, spec = _fixture(tmp_path)
    path = label_root / "P01_task_Lbr_1.mat"
    path.write_bytes(path.read_bytes() + b"tampered")

    with pytest.raises(SchemaError, match="byte-size mismatch"):
        audit_gaze_in_wild_source(label_root, process_root, spec)


def test_gaze_in_wild_source_audit_rejects_extra_unmanifested_process_file(tmp_path):
    label_root, process_root, spec = _fixture(tmp_path)
    _write_process(process_root / "unexpected.mat")

    with pytest.raises(SchemaError, match="process inventory"):
        audit_gaze_in_wild_source(label_root, process_root, spec)


def test_gaze_in_wild_source_audit_rejects_nonidentical_multi_labeller_timestamps(tmp_path):
    label_root, process_root, spec = _fixture(tmp_path)
    changed = label_root / "P01_task_Lbr_2.mat"
    _write_label(changed, labeller=2, time_offset_s=0.001)
    digest, size = _digest_record(changed)
    for record in spec.label_files:
        if record.path == "P01_task_Lbr_2.mat":
            record.sha256 = digest
            record.bytes = size
            break

    with pytest.raises(SchemaError, match="identical underlying gaze"):
        audit_gaze_in_wild_source(label_root, process_root, spec)


def test_template_cannot_certify_empirical_gaze_in_wild_data(tmp_path):
    label_root = tmp_path / "LabelData"
    process_root = tmp_path / "ProcessData"
    label_root.mkdir()
    process_root.mkdir()
    spec = GazeInWildSourceAuditSpec(
        dataset_name="Gaze-in-the-Wild",
        dataset_version="template",
        source="https://example.invalid/gaze-in-wild",
        source_revision="pending",
        license="Pending verification.",
        reuse_terms_source="https://example.invalid/terms",
    )

    with pytest.raises(SchemaError, match="Template"):
        audit_gaze_in_wild_source(label_root, process_root, spec)


def test_empirical_spec_rejects_missing_coordinate_verification():
    with pytest.raises(ValueError, match="coordinate"):
        GazeInWildSourceAuditSpec(
            dataset_name="Gaze-in-the-Wild",
            dataset_version="snapshot",
            source="https://example.invalid/gaze-in-wild",
            source_revision="abc",
            license="Verified terms.",
            reuse_terms_source="https://example.invalid/terms",
            dataset_status="empirical",
            reuse_terms_verified=True,
            analysis_use_permitted=True,
            participant_mapping_verified=True,
            participant_mapping_basis="Verified mapping.",
            label_files=[
                GazeInWildLabelFileRecord(
                    path="a_Lbr_1.mat",
                    sha256="a" * 64,
                    bytes=1,
                    participant_id="P01",
                    trial_id="T01",
                    labeller_id=1,
                    process_path="a.mat",
                )
            ],
            process_files=[
                GazeInWildProcessFileRecord(path="a.mat", sha256="b" * 64, bytes=1)
            ],
        )


def test_spec_rejects_duplicate_participant_trial_labeller_identity():
    process = GazeInWildProcessFileRecord(path="a.mat", sha256="b" * 64, bytes=1)
    labels = [
        GazeInWildLabelFileRecord(
            path=f"a_{index}_Lbr_1.mat",
            sha256=("a" if index == 1 else "c") * 64,
            bytes=1,
            participant_id="P01",
            trial_id="T01",
            labeller_id=1,
            process_path="a.mat",
        )
        for index in (1, 2)
    ]
    with pytest.raises(ValueError, match="identities must be unique"):
        GazeInWildSourceAuditSpec(
            dataset_name="Gaze-in-the-Wild",
            dataset_version="template",
            source="https://example.invalid/gaze-in-wild",
            source_revision="pending",
            license="Pending verification.",
            reuse_terms_source="https://example.invalid/terms",
            label_files=labels,
            process_files=[process],
        )


def test_source_audit_spec_json_loader_round_trips_template(tmp_path):
    path = tmp_path / "audit.json"
    path.write_text(
        json.dumps(
            {
                "dataset_name": "Gaze-in-the-Wild",
                "dataset_version": "template",
                "source": "https://example.invalid/gaze-in-wild",
                "source_revision": "pending",
                "license": "Pending verification.",
                "reuse_terms_source": "https://example.invalid/terms",
                "dataset_status": "template",
                "label_files": [],
                "process_files": [],
            }
        ),
        encoding="utf-8",
    )

    spec = load_gaze_in_wild_source_audit_spec(path)
    assert spec.dataset_name == "Gaze-in-the-Wild"
    assert spec.dataset_status == "template"
