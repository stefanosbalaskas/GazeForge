import numpy as np
import pandas as pd
import pytest

from gazeforge.cross_dataset import prepare_cross_dataset_event_benchmark
from gazeforge.downstream_lineage import validate_source_audit_lineage_binding
from gazeforge.exceptions import BenchmarkIntegrityError, SchemaError
from gazeforge.schema import GazeFrame
from gazeforge.source_audit_lineage import SourceAuditLineageReceipt

_REPORT = "a" * 64
_SPEC = "b" * 64
_MANIFEST = "c" * 64
_REVISION = "reviewed-revision"


def _dataset(name: str) -> GazeFrame:
    rows = []
    rate = 120.0
    dt = 1000.0 / rate
    for participant in ("P1", "P2"):
        for sample in range(90):
            if sample < 30:
                label = "fixation"
                x = 100.0 + 0.05 * sample
            elif sample < 60:
                label = "saccade"
                x = 110.0 + 6.0 * (sample - 30)
            else:
                label = "pursuit"
                x = 290.0 + 0.7 * (sample - 60)
            rows.append(
                {
                    "participant_id": participant,
                    "trial_id": f"{participant}_trial",
                    "timestamp_ms": sample * dt,
                    "x_px": x,
                    "y_px": 200.0 + 0.2 * np.sin(sample / 5.0),
                    "event_label": label,
                    "dataset_id": name,
                    "source_file": f"{participant}.synthetic",
                }
            )
    metadata = {
        "source_dataset": name,
        "participant_identity_resolved": True,
        "coordinate_source_unit": "pixels",
        "coordinate_unit_verified": True,
    }
    if name == "Hollywood2EM":
        metadata.update(
            {
                "source_audit_status": "verified",
                "source_audit_report_fingerprint_sha256": _REPORT,
                "source_audit_spec_fingerprint_sha256": _SPEC,
                "source_manifest_fingerprint_sha256": _MANIFEST,
                "source_revision": _REVISION,
                "reuse_terms_verified": True,
                "analysis_use_permitted": True,
            }
        )
    return GazeFrame(data=pd.DataFrame(rows), sampling_rate_hz=rate, metadata=metadata)


def _hollywood_lineage(
    *,
    dataset_key: str = "hollywood2em",
    report_fingerprint: str = _REPORT,
    spec_fingerprint: str = _SPEC,
    source_revision: str = _REVISION,
) -> SourceAuditLineageReceipt:
    return SourceAuditLineageReceipt(
        dataset_key=dataset_key,
        audit_template_fingerprint_sha256="d" * 64,
        authorization_fingerprint_sha256="e" * 64,
        authorized_spec_fingerprint_sha256=spec_fingerprint,
        audit_report_fingerprint_sha256=report_fingerprint,
        source_manifest_fingerprints_sha256=(
            {"source": _MANIFEST}
            if dataset_key == "hollywood2em"
            else {"label": _MANIFEST, "process": "f" * 64}
        ),
        source_revision=source_revision,
    )


def test_hollywood_cross_dataset_preparation_requires_lineage():
    with pytest.raises(SchemaError, match="lineage receipt"):
        prepare_cross_dataset_event_benchmark(
            {"Hollywood2EM": _dataset("Hollywood2EM"), "Other": _dataset("Other")},
            target_sampling_rate_hz=60.0,
        )


def test_hollywood_cross_dataset_preparation_stamps_matching_lineage():
    lineage = _hollywood_lineage()
    prepared = prepare_cross_dataset_event_benchmark(
        {"Hollywood2EM": _dataset("Hollywood2EM"), "Other": _dataset("Other")},
        source_audit_lineages={"Hollywood2EM": lineage},
        target_sampling_rate_hz=60.0,
    )
    fingerprint = lineage.to_dict()["receipt_fingerprint_sha256"]
    report = prepared.dataset_reports["Hollywood2EM"]
    assert report["source_audit_lineage_receipt_fingerprint_sha256"] == fingerprint
    hollywood = prepared.data.loc[prepared.data["dataset_id"] == "Hollywood2EM"]
    assert set(hollywood["source_audit_lineage_receipt_fingerprint_sha256"]) == {fingerprint}
    assert prepared.design["source_audit_lineage_policy"] == (
        "required_for_external_audited_datasets"
    )


def test_hollywood_cross_dataset_preparation_rejects_detached_lineage():
    detached = _hollywood_lineage(report_fingerprint="f" * 64)
    with pytest.raises(BenchmarkIntegrityError, match="lineage report fingerprint"):
        prepare_cross_dataset_event_benchmark(
            {"Hollywood2EM": _dataset("Hollywood2EM"), "Other": _dataset("Other")},
            source_audit_lineages={"Hollywood2EM": detached},
            target_sampling_rate_hz=60.0,
        )


@pytest.mark.parametrize(
    ("lineage", "message"),
    [
        (_hollywood_lineage(dataset_key="gaze-in-the-wild"), "lineage dataset"),
        (_hollywood_lineage(spec_fingerprint="0" * 64), "authorized-spec fingerprint"),
        (_hollywood_lineage(source_revision="other-revision"), "source revision"),
    ],
)
def test_generic_lineage_binding_rejects_identity_contract_mismatch(lineage, message):
    with pytest.raises(BenchmarkIntegrityError, match=message):
        validate_source_audit_lineage_binding(
            lineage,
            dataset_key="hollywood2em",
            audit_report_fingerprint_sha256=_REPORT,
            authorized_spec_fingerprint_sha256=_SPEC,
            source_manifest_fingerprints_sha256={"source": _MANIFEST},
            source_revision=_REVISION,
        )


def test_generic_lineage_binding_rejects_manifest_substitution():
    lineage = _hollywood_lineage()
    with pytest.raises(BenchmarkIntegrityError, match="manifest fingerprints"):
        validate_source_audit_lineage_binding(
            lineage,
            dataset_key="hollywood2em",
            audit_report_fingerprint_sha256=_REPORT,
            authorized_spec_fingerprint_sha256=_SPEC,
            source_manifest_fingerprints_sha256={"source": "0" * 64},
            source_revision=_REVISION,
        )


def test_generic_lineage_binding_rejects_non_hex_manifest_fingerprint():
    with pytest.raises(BenchmarkIntegrityError, match="invalid SHA-256"):
        validate_source_audit_lineage_binding(
            _hollywood_lineage(),
            dataset_key="hollywood2em",
            audit_report_fingerprint_sha256=_REPORT,
            authorized_spec_fingerprint_sha256=_SPEC,
            source_manifest_fingerprints_sha256={"source": "z" * 64},
            source_revision=_REVISION,
        )
