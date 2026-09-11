"""Preserve protocol-bound VISUS lineage across the existing source-authority suite seal."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .benchmarks import benchmark_fingerprint
from .exceptions import BenchmarkIntegrityError
from .visus_authority_binding import (
    AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD,
    source_authority_certificate_fingerprint,
)
from .visus_authority_execution import bind_visus_suite_to_source_authority
from .visus_protocol_validation import (
    VisusProtocolBoundValidationRun,
    validate_visus_protocol_bound_validation_run,
)
from .visus_suite import (
    VisusDynamicAOIValidationSuiteRun,
    validate_visus_dynamic_aoi_suite_manifest,
)

_TRANSITION_SCHEMA = "gazeforge-visus-protocol-authority-transition-v1"
_TRANSITION_FILENAME = "visus-protocol-authority-transition.json"
_SUITE_FINGERPRINT_FIELD = "suite_fingerprint_sha256"
_AUTHORITY_PROTOCOL_FLAG = "source_authority_certificate_bound"


@dataclass(slots=True)
class VisusProtocolAuthorityTransitionRun:
    """An immutable #130 validation plus a separately authority-bound suite clone."""

    validation: VisusProtocolBoundValidationRun
    authority_suite: VisusDynamicAOIValidationSuiteRun
    output_dir: Path
    transition_path: Path
    transition: dict[str, Any]
    transition_fingerprint_sha256: str


def _valid_sha256(value: Any) -> bool:
    text = str(value).strip().lower()
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text)


def _hash_regular_file(path: str | Path, *, label: str) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise BenchmarkIntegrityError(f"{label} must be a non-symlink regular file.")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise BenchmarkIntegrityError(f"{label} must be a non-symlink regular file.")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(f"{label} must be valid UTF-8 JSON.") from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(f"{label} must contain one JSON object.")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _assert_original_suite_unbound(validation: VisusProtocolBoundValidationRun) -> None:
    source = validation.suite.manifest.get("source")
    protocol = validation.suite.manifest.get("protocol")
    if not isinstance(source, Mapping) or not isinstance(protocol, Mapping):
        raise BenchmarkIntegrityError(
            "VISUS protocol-bound validation suite source/protocol structure is invalid."
        )
    if AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD in source:
        raise BenchmarkIntegrityError(
            "VISUS protocol-authority transition requires the original #130 suite "
            "to remain unbound."
        )
    if _AUTHORITY_PROTOCOL_FLAG in protocol or AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD in protocol:
        raise BenchmarkIntegrityError(
            "VISUS protocol-authority transition refuses an already authority-mutated "
            "original suite."
        )


def _resolved(path: Path) -> Path:
    return path.resolve(strict=False)


def _assert_separate_output(validation: VisusProtocolBoundValidationRun, output: Path) -> None:
    original = _resolved(validation.output_dir)
    target = _resolved(output)
    if target == original or original in target.parents:
        raise BenchmarkIntegrityError(
            "VISUS authority transition output must be separate from and outside the original "
            "protocol-bound validation directory."
        )


def _clone_suite(
    validation: VisusProtocolBoundValidationRun,
    output: Path,
) -> VisusDynamicAOIValidationSuiteRun:
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True, exist_ok=False)
    try:
        copied_reports: dict[str, Path] = {}
        seen_names: set[str] = set()
        for name, source_path in sorted(validation.suite.report_paths.items()):
            source = Path(source_path)
            _hash_regular_file(source, label=f"VISUS suite child {name!r}")
            if source.name in seen_names:
                raise BenchmarkIntegrityError(
                    "VISUS suite report filenames are not unique enough for an isolated clone."
                )
            seen_names.add(source.name)
            target = output / source.name
            shutil.copy2(source, target)
            copied_reports[name] = target

        manifest_source = validation.suite.manifest_path
        _hash_regular_file(manifest_source, label="VISUS suite manifest")
        manifest_target = output / manifest_source.name
        if manifest_target.name in seen_names:
            raise BenchmarkIntegrityError(
                "VISUS suite manifest filename collides with a child report filename."
            )
        shutil.copy2(manifest_source, manifest_target)

        clone = VisusDynamicAOIValidationSuiteRun(
            output_dir=output,
            report_paths=copied_reports,
            reports=copy.deepcopy(validation.suite.reports),
            manifest_path=manifest_target,
            manifest=copy.deepcopy(validation.suite.manifest),
            suite_fingerprint_sha256=validation.suite.suite_fingerprint_sha256,
        )
        verified = validate_visus_dynamic_aoi_suite_manifest(
            clone.manifest_path,
            verify_reports=True,
        )
        if verified[_SUITE_FINGERPRINT_FIELD] != clone.suite_fingerprint_sha256:
            raise BenchmarkIntegrityError(
                "Cloned VISUS suite does not reproduce the original suite fingerprint."
            )
        return clone
    except Exception:
        shutil.rmtree(output, ignore_errors=True)
        raise


def _pre_authority_projection_fingerprint(
    authority_manifest: Mapping[str, Any],
) -> str:
    body = {
        key: copy.deepcopy(value)
        for key, value in authority_manifest.items()
        if key != _SUITE_FINGERPRINT_FIELD
    }
    source = body.get("source")
    protocol = body.get("protocol")
    if not isinstance(source, dict) or not isinstance(protocol, dict):
        raise BenchmarkIntegrityError(
            "Authority-bound VISUS suite source/protocol structure is invalid."
        )
    source.pop(AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD, None)
    protocol.pop(_AUTHORITY_PROTOCOL_FLAG, None)
    protocol.pop(AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD, None)
    return benchmark_fingerprint(body)


def _child_file_ledger(
    original: VisusDynamicAOIValidationSuiteRun,
    authority_suite: VisusDynamicAOIValidationSuiteRun,
) -> list[dict[str, Any]]:
    if set(original.report_paths) != set(authority_suite.report_paths):
        raise BenchmarkIntegrityError(
            "VISUS authority suite child-report set differs from the original #130 suite."
        )
    records: list[dict[str, Any]] = []
    for name in sorted(original.report_paths):
        original_path = original.report_paths[name]
        authority_path = authority_suite.report_paths[name]
        if original_path.name != authority_path.name:
            raise BenchmarkIntegrityError(
                "VISUS authority transition changed a child-report filename."
            )
        original_sha = _hash_regular_file(
            original_path,
            label=f"Original VISUS suite child {name!r}",
        )
        authority_sha = _hash_regular_file(
            authority_path,
            label=f"Authority VISUS suite child {name!r}",
        )
        if authority_sha != original_sha:
            raise BenchmarkIntegrityError(
                "VISUS authority transition changed child-report bytes."
            )
        report = original.reports.get(name)
        if not isinstance(report, Mapping):
            raise BenchmarkIntegrityError(
                "Original VISUS suite child report object is missing."
            )
        report_fingerprint = str(report.get("report_fingerprint_sha256", ""))
        if not _valid_sha256(report_fingerprint):
            raise BenchmarkIntegrityError(
                "Original VISUS suite child report fingerprint is invalid."
            )
        records.append(
            {
                "name": name,
                "filename": original_path.name,
                "sha256": original_sha,
                "report_fingerprint_sha256": report_fingerprint,
            }
        )
    return records


def _verified_authority_suite(
    validation: VisusProtocolBoundValidationRun,
    authority_suite: VisusDynamicAOIValidationSuiteRun,
) -> tuple[dict[str, Any], str, str]:
    certificate_fingerprint = source_authority_certificate_fingerprint(
        validation.batch.audit,
        required=True,
    )
    assert certificate_fingerprint is not None
    verified = validate_visus_dynamic_aoi_suite_manifest(
        authority_suite.manifest_path,
        verify_reports=True,
    )
    if verified[_SUITE_FINGERPRINT_FIELD] != authority_suite.suite_fingerprint_sha256:
        raise BenchmarkIntegrityError(
            "Authority-bound VISUS suite object does not match its verified manifest."
        )

    manifest = _read_json_object(
        authority_suite.manifest_path,
        label="Authority-bound VISUS suite manifest",
    )
    if manifest.get(_SUITE_FINGERPRINT_FIELD) != authority_suite.suite_fingerprint_sha256:
        raise BenchmarkIntegrityError(
            "Authority-bound VISUS suite file does not match its suite object."
        )
    source = manifest.get("source")
    protocol = manifest.get("protocol")
    if not isinstance(source, Mapping) or not isinstance(protocol, Mapping):
        raise BenchmarkIntegrityError(
            "Authority-bound VISUS suite source/protocol sections are missing."
        )
    if source.get(AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD) != certificate_fingerprint:
        raise BenchmarkIntegrityError(
            "Authority-bound VISUS suite certificate differs from the source audit."
        )
    if protocol.get(_AUTHORITY_PROTOCOL_FLAG) is not True:
        raise BenchmarkIntegrityError(
            "Authority-bound VISUS suite lacks the required authority declaration."
        )
    if protocol.get(AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD) != certificate_fingerprint:
        raise BenchmarkIntegrityError(
            "Authority-bound VISUS suite protocol/source certificate identities differ."
        )

    pre_fingerprint = validation.suite.suite_fingerprint_sha256
    projection_fingerprint = _pre_authority_projection_fingerprint(manifest)
    if projection_fingerprint != pre_fingerprint:
        raise BenchmarkIntegrityError(
            "Authority-bound VISUS suite cannot reconstruct the exact pre-authority suite "
            "fingerprint by removing only authority fields."
        )
    if authority_suite.suite_fingerprint_sha256 == pre_fingerprint:
        raise BenchmarkIntegrityError(
            "VISUS authority transition did not create a distinct post-authority suite identity."
        )
    return manifest, certificate_fingerprint, projection_fingerprint


def _transition_body(
    validation: VisusProtocolBoundValidationRun,
    authority_suite: VisusDynamicAOIValidationSuiteRun,
    output: Path,
) -> dict[str, Any]:
    validation = validate_visus_protocol_bound_validation_run(validation)
    _assert_original_suite_unbound(validation)
    _assert_separate_output(validation, output)
    authority_manifest, certificate_fingerprint, projection_fingerprint = (
        _verified_authority_suite(
            validation,
            authority_suite,
        )
    )
    if _resolved(authority_suite.output_dir) != _resolved(output):
        raise BenchmarkIntegrityError(
            "VISUS authority-suite object is not rooted in the transition output directory."
        )
    if _resolved(authority_suite.manifest_path.parent) != _resolved(output):
        raise BenchmarkIntegrityError(
            "VISUS authority-suite manifest is outside the transition output directory."
        )

    original_binding_fingerprint = validation.binding_fingerprint_sha256
    if validation.binding.get("binding_fingerprint_sha256") != original_binding_fingerprint:
        raise BenchmarkIntegrityError(
            "VISUS protocol-validation object/binding fingerprint identity drifted."
        )
    if not _valid_sha256(original_binding_fingerprint):
        raise BenchmarkIntegrityError(
            "VISUS protocol-validation binding fingerprint is invalid."
        )

    source = validation.binding.get("source")
    if not isinstance(source, Mapping):
        raise BenchmarkIntegrityError(
            "VISUS protocol-validation source identity is missing."
        )

    child_reports = _child_file_ledger(validation.suite, authority_suite)
    return {
        "schema": _TRANSITION_SCHEMA,
        "status": "verified-protocol-authority-transition",
        "source": {
            **dict(source),
            AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD: certificate_fingerprint,
        },
        "protocol_fingerprint_sha256": validation.binding[
            "protocol_fingerprint_sha256"
        ],
        "protocol_batch_fingerprint_sha256": validation.binding[
            "protocol_batch_fingerprint_sha256"
        ],
        "protocol_validation_binding_filename": validation.binding_path.name,
        "protocol_validation_binding_file_sha256": _hash_regular_file(
            validation.binding_path,
            label="VISUS protocol-validation binding",
        ),
        "protocol_validation_binding_fingerprint_sha256": original_binding_fingerprint,
        "pre_authority_suite": {
            "manifest_filename": validation.suite.manifest_path.name,
            "manifest_sha256": _hash_regular_file(
                validation.suite.manifest_path,
                label="Original VISUS suite manifest",
            ),
            "suite_fingerprint_sha256": validation.suite.suite_fingerprint_sha256,
        },
        "post_authority_suite": {
            "manifest_filename": authority_suite.manifest_path.name,
            "manifest_sha256": _hash_regular_file(
                authority_suite.manifest_path,
                label="Authority-bound VISUS suite manifest",
            ),
            "suite_fingerprint_sha256": authority_suite.suite_fingerprint_sha256,
            "report_count": len(authority_manifest["reports"]),
        },
        "pre_authority_projection_fingerprint_sha256": projection_fingerprint,
        "child_reports": child_reports,
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
        "claim_limits": [
            (
                "This transition preserves the exact #130 protocol-validation artifact and binds "
                "an isolated suite clone to an already reviewed source-authority certificate."
            ),
            (
                "Removing only the authority fields from the cloned suite must reconstruct the "
                "exact pre-authority suite fingerprint."
            ),
            (
                "This transition does not replace the existing five-input authority execution "
                "provenance required to bind exact raw execution files and certificate bytes."
            ),
            (
                "Authority binding does not by itself promote model-human metrics to a reviewed "
                "empirical performance claim or Frozen Evidence."
            ),
        ],
    }


def run_visus_protocol_authority_transition(
    validation: VisusProtocolBoundValidationRun,
    output_dir: str | Path,
) -> VisusProtocolAuthorityTransitionRun:
    """Authority-bind an isolated clone while preserving the exact #130 validation directory."""
    validation = validate_visus_protocol_bound_validation_run(validation)
    _assert_original_suite_unbound(validation)
    source_authority_certificate_fingerprint(validation.batch.audit, required=True)

    output = Path(output_dir)
    _assert_separate_output(validation, output)
    clone = _clone_suite(validation, output)
    try:
        authority_suite = bind_visus_suite_to_source_authority(
            validation.batch.audit,
            clone,
        )
        body = _transition_body(validation, authority_suite, output)
        transition = {
            **body,
            "transition_fingerprint_sha256": benchmark_fingerprint(body),
        }
        transition_path = output / _TRANSITION_FILENAME
        _write_json(transition_path, transition)
        run = VisusProtocolAuthorityTransitionRun(
            validation=validation,
            authority_suite=authority_suite,
            output_dir=output,
            transition_path=transition_path,
            transition=transition,
            transition_fingerprint_sha256=transition[
                "transition_fingerprint_sha256"
            ],
        )
        return validate_visus_protocol_authority_transition(run)
    except Exception:
        shutil.rmtree(output, ignore_errors=True)
        raise


def validate_visus_protocol_authority_transition(
    run: VisusProtocolAuthorityTransitionRun,
) -> VisusProtocolAuthorityTransitionRun:
    """Replay the immutable pre-validation and post-authority transition chain."""
    if not isinstance(run, VisusProtocolAuthorityTransitionRun):
        raise TypeError("run must be a VisusProtocolAuthorityTransitionRun instance.")
    if run.transition_path.name != _TRANSITION_FILENAME:
        raise BenchmarkIntegrityError("VISUS protocol-authority transition filename drifted.")
    if _resolved(run.transition_path.parent) != _resolved(run.output_dir):
        raise BenchmarkIntegrityError(
            "VISUS protocol-authority transition file is outside its output directory."
        )

    transition = run.transition
    if transition.get("schema") != _TRANSITION_SCHEMA:
        raise BenchmarkIntegrityError("VISUS protocol-authority transition schema drifted.")
    if transition.get("status") != "verified-protocol-authority-transition":
        raise BenchmarkIntegrityError("VISUS protocol-authority transition status drifted.")
    claimed = str(transition.get("transition_fingerprint_sha256", ""))
    body = {
        key: value
        for key, value in transition.items()
        if key != "transition_fingerprint_sha256"
    }
    if not _valid_sha256(claimed) or benchmark_fingerprint(body) != claimed:
        raise BenchmarkIntegrityError(
            "VISUS protocol-authority transition fingerprint does not revalidate."
        )
    if claimed != run.transition_fingerprint_sha256:
        raise BenchmarkIntegrityError(
            "VISUS protocol-authority transition object fingerprint drifted."
        )
    if _read_json_object(
        run.transition_path,
        label="VISUS protocol-authority transition",
    ) != transition:
        raise BenchmarkIntegrityError(
            "VISUS protocol-authority transition file/object content drifted."
        )

    expected = _transition_body(
        run.validation,
        run.authority_suite,
        run.output_dir,
    )
    if body != expected:
        raise BenchmarkIntegrityError(
            "VISUS protocol-authority transition no longer matches current lineage."
        )

    semantics = transition.get("transition_semantics")
    if not isinstance(semantics, Mapping) or any(
        semantics.get(field) is not True
        for field in (
            "original_protocol_validation_preserved",
            "authority_binding_applied_to_isolated_suite_clone",
            "only_suite_manifest_authority_fields_added",
            "child_report_bytes_unchanged",
            "authority_execution_provenance_required_separately",
        )
    ):
        raise BenchmarkIntegrityError(
            "VISUS protocol-authority transition semantics were weakened."
        )
    if transition.get("source_authority_certificate_consumed") is not True:
        raise BenchmarkIntegrityError(
            "VISUS protocol-authority transition lost its certificate-consumption status."
        )
    for field in (
        "empirical_validation_authorized_by_transition",
        "empirical_performance_claim_created",
        "formal_preregistration_verified",
        "frozen_evidence_created",
        "raw_source_redistribution_action_authorized",
    ):
        if transition.get(field) is not False:
            raise BenchmarkIntegrityError(
                f"VISUS protocol-authority transition cannot promote {field}."
            )
    return run
