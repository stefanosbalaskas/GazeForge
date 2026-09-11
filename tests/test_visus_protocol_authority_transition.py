import copy
import json
from pathlib import Path

import pandas as pd
import pytest
from test_visus_preexecution_protocol import _FakeRuntime, _fixture, _freeze
from test_visus_protocol_validation import _case as _unbound_case

from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.visus_authority_binding import (
    AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD,
    audit_visus_source_with_authority,
)
from gazeforge.visus_authority_execution import snapshot_visus_authority_execution_inputs
from gazeforge.visus_authority_execution_strict import (
    build_visus_authority_execution_provenance,
    validate_visus_authority_execution_provenance,
    write_visus_authority_execution_provenance,
)
from gazeforge.visus_intake import prepare_visus_canonical_aoi_intake
from gazeforge.visus_protocol_authority_transition import (
    run_visus_protocol_authority_transition,
    validate_visus_protocol_authority_transition,
)
from gazeforge.visus_protocol_batch import run_visus_grounded_sam2_protocol_batch
from gazeforge.visus_protocol_validation import (
    run_visus_protocol_bound_validation_suite,
    validate_visus_protocol_bound_validation_run,
)

from _visus_authority_fixture import (
    build_visus_authority_certificate,
    write_visus_authority_certificate,
)


def _reference_table(batch):
    rows = []
    for stimulus_id, plan in batch.plans_by_stimulus.items():
        label = plan.labels[0]
        for frame_index in (0, 1):
            rows.append(
                {
                    "source_path": f"aoi/{stimulus_id}.xml",
                    "stimulus_id": stimulus_id,
                    "annotation_stream_id": "published_curated",
                    "frame_index": frame_index,
                    "aoi_id": f"human-{stimulus_id}",
                    "label": label,
                    "xmin": 1.0,
                    "ymin": 1.0,
                    "xmax": 4.0,
                    "ymax": 4.0,
                }
            )
    return pd.DataFrame(rows)


def _bound_case(tmp_path: Path):
    root = tmp_path / "case"
    root.mkdir()
    structural_audit, plans, timestamps, _ = _fixture(root)
    certificate = build_visus_authority_certificate(structural_audit.spec)
    bound_audit = audit_visus_source_with_authority(
        root / "source",
        structural_audit.spec,
        certificate,
    )
    certificate_path = write_visus_authority_certificate(
        root / "visus-source-authority-certificate.json",
        certificate,
    )
    spec_path = root / "visus-source-audit.json"
    spec_path.write_text(
        json.dumps(bound_audit.spec.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    grid_path = root / "timestamp-grid.json"
    grid_path.write_text(
        json.dumps(timestamps, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    frozen = _freeze(root, bound_audit, plans, timestamps)
    batch = run_visus_grounded_sam2_protocol_batch(
        frozen,
        bound_audit,
        plans,
        root / "batch",
        runtime=_FakeRuntime(),
    )
    human_table = _reference_table(batch)
    human_path = root / "human-reference.csv"
    human_table.to_csv(human_path, index=False)
    reference = prepare_visus_canonical_aoi_intake(
        bound_audit,
        human_table,
        extraction_basis="Reviewed fixture extraction from exact audited AOI XML files.",
        frame_index_base=0,
    )
    validation = run_visus_protocol_bound_validation_suite(
        batch,
        reference,
        root / "validation",
    )
    return {
        "root": root,
        "audit": bound_audit,
        "certificate": certificate,
        "certificate_path": certificate_path,
        "spec_path": spec_path,
        "grid_path": grid_path,
        "human_path": human_path,
        "batch": batch,
        "reference": reference,
        "validation": validation,
    }


def _transition(tmp_path: Path):
    case = _bound_case(tmp_path)
    run = run_visus_protocol_authority_transition(
        case["validation"],
        case["root"] / "authority-transition",
    )
    return case, run


def _resign_suite(run, manifest):
    body = {
        key: value
        for key, value in manifest.items()
        if key != "suite_fingerprint_sha256"
    }
    manifest["suite_fingerprint_sha256"] = benchmark_fingerprint(body)
    run.authority_suite.manifest = manifest
    run.authority_suite.suite_fingerprint_sha256 = manifest[
        "suite_fingerprint_sha256"
    ]
    run.authority_suite.manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _rewrite_transition(run, payload):
    body = {
        key: value
        for key, value in payload.items()
        if key != "transition_fingerprint_sha256"
    }
    payload["transition_fingerprint_sha256"] = benchmark_fingerprint(body)
    run.transition = payload
    run.transition_fingerprint_sha256 = payload["transition_fingerprint_sha256"]
    run.transition_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_transition_preserves_original_protocol_validation_bytes(tmp_path):
    case = _bound_case(tmp_path)
    validation = case["validation"]
    binding_before = validation.binding_path.read_bytes()
    manifest_before = validation.suite.manifest_path.read_bytes()
    children_before = {
        name: path.read_bytes()
        for name, path in validation.suite.report_paths.items()
    }

    run = run_visus_protocol_authority_transition(
        validation,
        case["root"] / "authority-transition",
    )

    assert validation.binding_path.read_bytes() == binding_before
    assert validation.suite.manifest_path.read_bytes() == manifest_before
    assert {
        name: path.read_bytes()
        for name, path in validation.suite.report_paths.items()
    } == children_before
    assert validate_visus_protocol_bound_validation_run(validation) is validation
    assert validate_visus_protocol_authority_transition(run) is run


def test_transition_authority_binds_only_isolated_suite_clone(tmp_path):
    case, run = _transition(tmp_path)
    certificate_fp = case["certificate"]["certificate_fingerprint_sha256"]

    assert run.authority_suite.output_dir != case["validation"].output_dir
    assert run.authority_suite.manifest["source"][
        AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD
    ] == certificate_fp
    assert run.authority_suite.manifest["protocol"][
        "source_authority_certificate_bound"
    ] is True
    assert run.authority_suite.manifest["protocol"][
        AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD
    ] == certificate_fp
    assert AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD not in (
        case["validation"].suite.manifest["source"]
    )


def test_transition_projection_recovers_exact_pre_authority_suite(tmp_path):
    case, run = _transition(tmp_path)

    assert run.transition["pre_authority_projection_fingerprint_sha256"] == (
        case["validation"].suite.suite_fingerprint_sha256
    )
    assert run.transition["pre_authority_suite"]["suite_fingerprint_sha256"] == (
        case["validation"].suite.suite_fingerprint_sha256
    )
    assert run.transition["post_authority_suite"]["suite_fingerprint_sha256"] == (
        run.authority_suite.suite_fingerprint_sha256
    )
    assert run.authority_suite.suite_fingerprint_sha256 != (
        case["validation"].suite.suite_fingerprint_sha256
    )


def test_transition_child_reports_are_byte_identical(tmp_path):
    case, run = _transition(tmp_path)

    assert set(case["validation"].suite.report_paths) == set(
        run.authority_suite.report_paths
    )
    for name, original in case["validation"].suite.report_paths.items():
        copied = run.authority_suite.report_paths[name]
        assert copied.read_bytes() == original.read_bytes()


def test_transition_rejects_unbound_source_audit(tmp_path):
    validation, _, _ = _unbound_case(tmp_path)

    with pytest.raises(BenchmarkIntegrityError, match="authority-bound source audit"):
        run_visus_protocol_authority_transition(
            validation,
            tmp_path / "authority-transition",
        )


def test_transition_refuses_to_write_inside_original_validation_directory(tmp_path):
    case = _bound_case(tmp_path)
    validation = case["validation"]

    with pytest.raises(BenchmarkIntegrityError, match="outside the original"):
        run_visus_protocol_authority_transition(
            validation,
            validation.output_dir / "authority",
        )


def test_transition_rejects_original_binding_byte_drift(tmp_path):
    case, run = _transition(tmp_path)
    case["validation"].binding_path.write_bytes(
        case["validation"].binding_path.read_bytes() + b"\n"
    )

    with pytest.raises(BenchmarkIntegrityError, match="current lineage"):
        validate_visus_protocol_authority_transition(run)


def test_transition_rejects_original_suite_manifest_byte_drift(tmp_path):
    case, run = _transition(tmp_path)
    case["validation"].suite.manifest_path.write_bytes(
        case["validation"].suite.manifest_path.read_bytes() + b"\n"
    )

    with pytest.raises(BenchmarkIntegrityError, match="current lineage"):
        validate_visus_protocol_authority_transition(run)


def test_transition_rejects_authority_child_report_byte_drift(tmp_path):
    _, run = _transition(tmp_path)
    path = next(iter(run.authority_suite.report_paths.values()))
    path.write_bytes(path.read_bytes() + b"\n")

    with pytest.raises(BenchmarkIntegrityError, match="changed child-report bytes"):
        validate_visus_protocol_authority_transition(run)


def test_transition_rejects_resigned_certificate_substitution(tmp_path):
    _, run = _transition(tmp_path)
    manifest = copy.deepcopy(run.authority_suite.manifest)
    manifest["source"][AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD] = "f" * 64
    manifest["protocol"][AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD] = "f" * 64
    _resign_suite(run, manifest)

    with pytest.raises(BenchmarkIntegrityError, match="differs from the source audit"):
        validate_visus_protocol_authority_transition(run)


def test_transition_rejects_resigned_non_authority_suite_mutation(tmp_path):
    _, run = _transition(tmp_path)
    manifest = copy.deepcopy(run.authority_suite.manifest)
    manifest["unexpected_posthoc_field"] = "not-authority-metadata"
    _resign_suite(run, manifest)

    with pytest.raises(BenchmarkIntegrityError, match="pre-authority suite fingerprint"):
        validate_visus_protocol_authority_transition(run)


def test_transition_rejects_resigned_claim_promotion(tmp_path):
    _, run = _transition(tmp_path)
    payload = copy.deepcopy(run.transition)
    payload["empirical_performance_claim_created"] = True
    _rewrite_transition(run, payload)

    with pytest.raises(BenchmarkIntegrityError, match="current lineage"):
        validate_visus_protocol_authority_transition(run)


def test_transition_preserves_scientific_boundaries(tmp_path):
    _, run = _transition(tmp_path)

    assert run.transition["source_authority_certificate_consumed"] is True
    assert run.transition["transition_semantics"][
        "authority_execution_provenance_required_separately"
    ] is True
    for field in (
        "empirical_validation_authorized_by_transition",
        "empirical_performance_claim_created",
        "formal_preregistration_verified",
        "frozen_evidence_created",
        "raw_source_redistribution_action_authorized",
    ):
        assert run.transition[field] is False


def test_transitioned_suite_is_accepted_by_existing_strict_authority_execution(tmp_path):
    case, run = _transition(tmp_path)
    snapshots = snapshot_visus_authority_execution_inputs(
        source_audit_spec=case["spec_path"],
        source_authority_certificate=case["certificate_path"],
        human_aoi_table=case["human_path"],
        model_prediction_table=case["batch"].prediction_path,
        timestamp_grid_json=case["grid_path"],
    )
    manifest = build_visus_authority_execution_provenance(
        case["audit"],
        run.authority_suite,
        snapshots,
    )
    provenance = write_visus_authority_execution_provenance(
        manifest,
        run.output_dir,
    )
    summary = validate_visus_authority_execution_provenance(
        provenance.manifest_path,
        verify_suite=True,
    )

    assert summary["status"] == "complete"
    assert summary["suite_fingerprint_sha256"] == (
        run.authority_suite.suite_fingerprint_sha256
    )
    assert summary[AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD] == (
        case["certificate"]["certificate_fingerprint_sha256"]
    )
    assert summary["authority_certificate_semantics_verified"] is True
