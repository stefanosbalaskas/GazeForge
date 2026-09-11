import hashlib
import json
from pathlib import Path

import pytest
from test_visus_protocol_authority_transition import _transition

from gazeforge import visus_evidence
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.visus_authority_binding import AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD
from gazeforge.visus_authority_execution import snapshot_visus_authority_execution_inputs
from gazeforge.visus_authority_execution_strict import (
    build_visus_authority_execution_provenance,
    write_visus_authority_execution_provenance,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _signed(payload, field):
    body = {key: value for key, value in payload.items() if key != field}
    return {**body, field: benchmark_fingerprint(body)}


def _suite_summary():
    authority = "e" * 64
    reports = []
    for index, name in enumerate(
        ("human_reference_intake", "model_prediction_intake", "model_human_validation"),
        start=1,
    ):
        reports.append(
            {
                "name": name,
                "path": f"{name}.json",
                "report_fingerprint_sha256": str(index) * 64,
            }
        )
    return {
        "suite": "visus-dynamic-aoi-validation-v1",
        "status": "complete",
        "report_count": 3,
        "reports": reports,
        "suite_fingerprint_sha256": "a" * 64,
        "source": {
            "source_audit_report_fingerprint_sha256": "b" * 64,
            "source_audit_spec_fingerprint_sha256": "c" * 64,
            "source_manifest_fingerprint_sha256": "d" * 64,
            AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD: authority,
        },
        "protocol": {
            "reference_stream_id": "annotator_a",
            "prediction_emission_grid_used": False,
            "human_human_agreement_included": False,
            "source_authority_certificate_bound": True,
            AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD: authority,
        },
    }


def _execution_summary():
    return {
        "schema": "gazeforge-visus-execution-provenance-v2",
        "status": "complete",
        "input_count": 5,
        "suite_fingerprint_sha256": "a" * 64,
        "execution_fingerprint_sha256": "f" * 64,
        AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD: "e" * 64,
        "authority_certificate_semantics_verified": True,
        "suite_verified": True,
    }


def _synthetic_bundle(tmp_path):
    root = tmp_path / "case" / "authority-transition"
    validation_root = tmp_path / "case" / "validation"
    root.mkdir(parents=True)
    validation_root.mkdir(parents=True)
    suite = _suite_summary()

    suite_path = root / "visus-dynamic-aoi-suite-manifest.json"
    execution_path = root / "visus-execution-provenance.json"
    _write(suite_path, {"placeholder": True})
    _write(execution_path, {"placeholder": True})

    child_rows = []
    for record in suite["reports"]:
        child_path = root / record["path"]
        _write(child_path, {"name": record["name"]})
        child_rows.append(
            {
                "name": record["name"],
                "filename": child_path.name,
                "sha256": _sha(child_path),
                "report_fingerprint_sha256": record["report_fingerprint_sha256"],
            }
        )

    binding = {
        "schema": "gazeforge-visus-protocol-bound-validation-v1",
        "status": "verified-protocol-bound-validation",
        "source": {
            "source_audit_report_fingerprint_sha256": "b" * 64,
            "source_audit_spec_fingerprint_sha256": "c" * 64,
            "source_manifest_fingerprint_sha256": "d" * 64,
        },
        "protocol_fingerprint_sha256": "4" * 64,
        "protocol_batch_fingerprint_sha256": "5" * 64,
        "frozen_evaluation": {
            "reference_stream_id": "annotator_a",
            "timestamp_grid_basis": "external fixture grid",
            "timestamp_grid_fingerprints": {"S1": "6" * 64},
            "max_interpolation_gap_ms": 80.0,
            "min_iou": 0.5,
            "require_label_match": True,
            "fixation_assignment_planned": False,
            "overlap_rule": "highest_confidence",
            "prediction_emission_grid_used": False,
        },
        "validation_suite_fingerprint_sha256": "9" * 64,
        "model_human_validation_executed": True,
        "source_authority_certificate_required_separately": True,
        "source_authority_certificate_bound_by_this_layer": False,
        "formal_preregistration_verified": False,
        "empirical_performance_claim_created": False,
        "dataset_source_authority_promoted": False,
        "dataset_rights_promoted": False,
        "frozen_evidence_created": False,
    }
    binding = _signed(binding, "binding_fingerprint_sha256")
    binding_path = validation_root / "visus-protocol-bound-validation.json"
    _write(binding_path, binding)

    transition = {
        "schema": "gazeforge-visus-protocol-authority-transition-v1",
        "status": "verified-protocol-authority-transition",
        "source": dict(suite["source"]),
        "protocol_fingerprint_sha256": binding["protocol_fingerprint_sha256"],
        "protocol_batch_fingerprint_sha256": binding["protocol_batch_fingerprint_sha256"],
        "protocol_validation_binding_filename": binding_path.name,
        "protocol_validation_binding_file_sha256": _sha(binding_path),
        "protocol_validation_binding_fingerprint_sha256": binding[
            "binding_fingerprint_sha256"
        ],
        "pre_authority_suite": {
            "manifest_filename": suite_path.name,
            "manifest_sha256": "7" * 64,
            "suite_fingerprint_sha256": "9" * 64,
        },
        "post_authority_suite": {
            "manifest_filename": suite_path.name,
            "manifest_sha256": _sha(suite_path),
            "suite_fingerprint_sha256": suite["suite_fingerprint_sha256"],
            "report_count": suite["report_count"],
        },
        "pre_authority_projection_fingerprint_sha256": "9" * 64,
        "child_reports": child_rows,
        "transition_semantics": {
            "original_protocol_validation_preserved": True,
            "authority_binding_applied_to_isolated_suite_clone": True,
            "only_suite_manifest_authority_fields_added": True,
            "child_report_bytes_unchanged": True,
            "authority_execution_provenance_required_separately": True,
        },
        "source_authority_certificate_consumed": True,
        "empirical_validation_authorized_by_transition": False,
        "empirical_performance_claim_created": False,
        "formal_preregistration_verified": False,
        "frozen_evidence_created": False,
        "raw_source_redistribution_action_authorized": False,
    }
    transition = _signed(transition, "transition_fingerprint_sha256")
    transition_path = root / "visus-protocol-authority-transition.json"
    _write(transition_path, transition)
    return root, suite, binding_path, transition_path


def _mock_validators(monkeypatch, suite, execution=None):
    monkeypatch.setattr(
        visus_evidence,
        "validate_visus_dynamic_aoi_suite_manifest",
        lambda path, verify_reports=True: suite,
    )
    monkeypatch.setattr(
        visus_evidence,
        "validate_visus_authority_execution_provenance",
        lambda path, verify_suite=True: _execution_summary() if execution is None else execution,
    )


def _resign_transition(path: Path, mutate):
    payload = json.loads(path.read_text(encoding="utf-8"))
    mutate(payload)
    payload = _signed(payload, "transition_fingerprint_sha256")
    _write(path, payload)


def _resign_binding_and_transition(binding_path: Path, transition_path: Path, mutate):
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    mutate(binding)
    binding = _signed(binding, "binding_fingerprint_sha256")
    _write(binding_path, binding)
    transition = json.loads(transition_path.read_text(encoding="utf-8"))
    transition["protocol_validation_binding_file_sha256"] = _sha(binding_path)
    transition["protocol_validation_binding_fingerprint_sha256"] = binding[
        "binding_fingerprint_sha256"
    ]
    transition = _signed(transition, "transition_fingerprint_sha256")
    _write(transition_path, transition)


def test_frozen_evidence_v3_rejects_legacy_suite_execution_pair(tmp_path):
    root = tmp_path / "bundle"
    root.mkdir()
    _write(root / "visus-dynamic-aoi-suite-manifest.json", {"placeholder": True})
    _write(root / "visus-execution-provenance.json", {"placeholder": True})

    with pytest.raises(BenchmarkIntegrityError, match="protocol-authority transition"):
        visus_evidence.validate_visus_frozen_evidence_bundle(root)


def test_frozen_evidence_v3_accepts_complete_protocol_lineage(monkeypatch, tmp_path):
    root, suite, binding_path, _ = _synthetic_bundle(tmp_path)
    _mock_validators(monkeypatch, suite)

    summary = visus_evidence.validate_visus_frozen_evidence_bundle(root)
    assert summary["bundle"] == "visus-frozen-evidence-v3"
    assert summary["status"] == "verified-protocol-authority-bound-bundle"
    assert summary["protocol_bound_lineage_verified"] is True
    assert summary["frozen_evidence_eligible_for_scientific_review"] is True
    assert summary["scientific_review_completed"] is False
    assert summary["empirical_performance_claim_created"] is False
    assert summary["formal_preregistration_verified"] is False
    assert summary["raw_execution_input_count"] == 5
    assert Path(summary["protocol_validation_binding_path"]) == binding_path
    assert all(summary["lineage"].values())


def test_frozen_evidence_v3_typed_bundle_carries_lineage_ids(monkeypatch, tmp_path):
    root, suite, binding_path, _ = _synthetic_bundle(tmp_path)
    _mock_validators(monkeypatch, suite)

    typed = visus_evidence.load_visus_frozen_evidence_bundle(
        root / "visus-execution-provenance.json"
    )
    assert typed.root == root
    assert typed.protocol_validation_binding_path == binding_path
    assert typed.transition_fingerprint_sha256
    assert typed.protocol_validation_binding_fingerprint_sha256
    assert typed.protocol_fingerprint_sha256 == "4" * 64
    assert typed.protocol_batch_fingerprint_sha256 == "5" * 64


def test_frozen_evidence_v3_accepts_explicit_protocol_binding(monkeypatch, tmp_path):
    root, suite, binding_path, _ = _synthetic_bundle(tmp_path)
    duplicate = tmp_path / "case" / "duplicate" / binding_path.name
    duplicate.parent.mkdir()
    duplicate.write_bytes(binding_path.read_bytes())
    _mock_validators(monkeypatch, suite)

    summary = visus_evidence.validate_visus_frozen_evidence_bundle(
        root,
        protocol_validation_binding_path=binding_path,
    )
    assert Path(summary["protocol_validation_binding_path"]) == binding_path


def test_frozen_evidence_v3_rejects_ambiguous_binding_lookup(monkeypatch, tmp_path):
    root, suite, binding_path, _ = _synthetic_bundle(tmp_path)
    duplicate = tmp_path / "case" / "duplicate" / binding_path.name
    duplicate.parent.mkdir()
    duplicate.write_bytes(binding_path.read_bytes())
    _mock_validators(monkeypatch, suite)

    with pytest.raises(BenchmarkIntegrityError, match="ambiguous"):
        visus_evidence.validate_visus_frozen_evidence_bundle(root)


def test_frozen_evidence_v3_rejects_transition_fingerprint_tamper(monkeypatch, tmp_path):
    root, suite, _, transition_path = _synthetic_bundle(tmp_path)
    payload = json.loads(transition_path.read_text(encoding="utf-8"))
    payload["status"] = "tampered"
    _write(transition_path, payload)
    _mock_validators(monkeypatch, suite)

    with pytest.raises(BenchmarkIntegrityError, match="status is invalid"):
        visus_evidence.validate_visus_frozen_evidence_bundle(root)


def test_frozen_evidence_v3_rejects_transition_claim_promotion(monkeypatch, tmp_path):
    root, suite, _, transition_path = _synthetic_bundle(tmp_path)
    _resign_transition(
        transition_path,
        lambda payload: payload.__setitem__("empirical_performance_claim_created", True),
    )
    _mock_validators(monkeypatch, suite)

    with pytest.raises(BenchmarkIntegrityError, match="cannot promote"):
        visus_evidence.validate_visus_frozen_evidence_bundle(root)


def test_frozen_evidence_v3_rejects_protocol_binding_byte_drift(monkeypatch, tmp_path):
    root, suite, binding_path, _ = _synthetic_bundle(tmp_path)
    binding_path.write_bytes(binding_path.read_bytes() + b"\n")
    _mock_validators(monkeypatch, suite)

    with pytest.raises(BenchmarkIntegrityError, match="cannot locate the exact"):
        visus_evidence.validate_visus_frozen_evidence_bundle(root)


def test_frozen_evidence_v3_rejects_resigned_protocol_claim_promotion(monkeypatch, tmp_path):
    root, suite, binding_path, transition_path = _synthetic_bundle(tmp_path)
    _resign_binding_and_transition(
        binding_path,
        transition_path,
        lambda binding: binding.__setitem__("frozen_evidence_created", True),
    )
    _mock_validators(monkeypatch, suite)

    with pytest.raises(BenchmarkIntegrityError, match="cannot promote frozen_evidence_created"):
        visus_evidence.validate_visus_frozen_evidence_bundle(root)


def test_frozen_evidence_v3_rejects_child_report_byte_drift(monkeypatch, tmp_path):
    root, suite, _, _ = _synthetic_bundle(tmp_path)
    child = root / suite["reports"][0]["path"]
    child.write_bytes(child.read_bytes() + b"\n")
    _mock_validators(monkeypatch, suite)

    with pytest.raises(BenchmarkIntegrityError, match="child-report bytes drifted"):
        visus_evidence.validate_visus_frozen_evidence_bundle(root)


def test_frozen_evidence_v3_rejects_cross_manifest_mismatch(monkeypatch, tmp_path):
    root, suite, _, _ = _synthetic_bundle(tmp_path)
    execution = _execution_summary()
    execution["suite_fingerprint_sha256"] = "0" * 64
    _mock_validators(monkeypatch, suite, execution)

    with pytest.raises(BenchmarkIntegrityError, match="fingerprints disagree"):
        visus_evidence.validate_visus_frozen_evidence_bundle(root)


def test_frozen_evidence_v3_rejects_legacy_four_raw_inputs(monkeypatch, tmp_path):
    root, suite, _, _ = _synthetic_bundle(tmp_path)
    execution = _execution_summary()
    execution["input_count"] = 4
    _mock_validators(monkeypatch, suite, execution)

    with pytest.raises(BenchmarkIntegrityError, match="exactly five raw inputs"):
        visus_evidence.validate_visus_frozen_evidence_bundle(root)


def test_frozen_evidence_v3_rejects_unverified_certificate_semantics(monkeypatch, tmp_path):
    root, suite, _, _ = _synthetic_bundle(tmp_path)
    execution = _execution_summary()
    execution["authority_certificate_semantics_verified"] = False
    _mock_validators(monkeypatch, suite, execution)

    with pytest.raises(BenchmarkIntegrityError, match="did not revalidate"):
        visus_evidence.validate_visus_frozen_evidence_bundle(root)


def test_frozen_evidence_v3_accepts_real_protocol_transition_and_strict_execution(tmp_path):
    case, transition = _transition(tmp_path)
    snapshots = snapshot_visus_authority_execution_inputs(
        source_audit_spec=case["spec_path"],
        source_authority_certificate=case["certificate_path"],
        human_aoi_table=case["human_path"],
        model_prediction_table=case["batch"].prediction_path,
        timestamp_grid_json=case["grid_path"],
    )
    manifest = build_visus_authority_execution_provenance(
        case["audit"],
        transition.authority_suite,
        snapshots,
    )
    write_visus_authority_execution_provenance(
        manifest,
        transition.output_dir,
    )

    summary = visus_evidence.validate_visus_frozen_evidence_bundle(
        transition.output_dir,
        protocol_validation_binding_path=case["validation"].binding_path,
    )
    assert summary["bundle"] == "visus-frozen-evidence-v3"
    assert summary["protocol_bound_lineage_verified"] is True
    assert summary["suite_fingerprint_sha256"] == (
        transition.authority_suite.suite_fingerprint_sha256
    )
    assert summary["pre_authority_suite_fingerprint_sha256"] == (
        case["validation"].suite.suite_fingerprint_sha256
    )
    assert summary["transition_fingerprint_sha256"] == (
        transition.transition_fingerprint_sha256
    )


def test_frozen_evidence_bundle_rejects_unrelated_file_path(tmp_path):
    unrelated = tmp_path / "something.json"
    unrelated.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="suite directory"):
        visus_evidence.validate_visus_frozen_evidence_bundle(unrelated)
