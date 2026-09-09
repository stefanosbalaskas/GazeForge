from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.hollywood2_gin_rights_model_exhaustion import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
    evidence_fingerprint,
    validate_hollywood2_gin_rights_model_exhaustion,
)

EVIDENCE = Path(
    "validation/evidence/hollywood2/hollywood2-gin-rights-model-exhaustion-evidence-v1.json"
)
AUTHOR = Path(
    "validation/evidence/hollywood2/hollywood2-author-license-statement-evidence-v1.json"
)


def _record() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def _set_nested(record: dict, path: tuple[str, ...], value: object) -> dict:
    out = copy.deepcopy(record)
    cursor = out
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    out["evidence_fingerprint_sha256"] = evidence_fingerprint(out)
    return out


def test_frozen_rights_model_evidence_validates() -> None:
    record = validate_hollywood2_gin_rights_model_exhaustion(EVIDENCE)
    assert record["evidence_fingerprint_sha256"] == EXPECTED_EVIDENCE_FINGERPRINT_SHA256
    rights = record["rights_model_interpretation"]
    assert rights["dataset_license_is_modeled_as_repository_specific_metadata"] is True
    assert rights["exact_hollywood2em_license_identifier_recovered"] is False
    assert rights["analysis_use_authorized"] is False
    assert rights["raw_data_redistribution_authorized"] is False


def test_rejects_invalid_self_fingerprint() -> None:
    record = _record()
    record["evidence_fingerprint_sha256"] = "0" * 64
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_gin_rights_model_exhaustion(record)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("rights_model_interpretation", "gin_public_access_is_dataset_license"), True),
        (("rights_model_interpretation", "gin_software_mit_license_is_dataset_license"), True),
        (
            (
                "rights_model_interpretation",
                "gin_service_assigns_one_automatic_license_to_all_public_datasets",
            ),
            True,
        ),
        (
            (
                "rights_model_interpretation",
                "dataset_license_is_modeled_as_repository_specific_metadata",
            ),
            False,
        ),
        (
            ("rights_model_interpretation", "exact_hollywood2em_license_identifier_recovered"),
            True,
        ),
        (("rights_model_interpretation", "exact_hollywood2em_license_text_recovered"), True),
        (("rights_model_interpretation", "analysis_use_authorized"), True),
        (("rights_model_interpretation", "raw_data_redistribution_authorized"), True),
        (("rights_model_interpretation", "rights_roadmap_component_resolved"), True),
        (("scientific_boundary", "participant_identity_mapping_verified"), True),
        (("scientific_boundary", "source_audit_ready"), True),
        (("scientific_boundary", "participant_disjoint_model_validation_created"), True),
        (("scientific_boundary", "cross_dataset_validation_created"), True),
        (("scientific_boundary", "independent_human_human_agreement_created"), True),
        (("scientific_boundary", "frozen_evidence_performance_claim_created"), True),
        (("scientific_boundary", "new_empirical_performance_claim_created"), True),
        (("scientific_boundary", "native_60hz_or_gp3_validity_created"), True),
        (
            (
                "gin_first_party_infrastructure_evidence",
                "gogs",
                "software_license_applies_to_hollywood2em_data",
            ),
            True,
        ),
    ],
)
def test_rejects_refingerprinted_promotion(path: tuple[str, ...], value: object) -> None:
    record = _set_nested(_record(), path, value)
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_gin_rights_model_exhaustion(record)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("gin_first_party_infrastructure_evidence", "gogs", "commit_sha1"), "0" * 40),
        (("gin_first_party_infrastructure_evidence", "gogs", "readme_blob_sha1"), "0" * 40),
        (("gin_first_party_infrastructure_evidence", "libgin", "commit_sha1"), "0" * 40),
        (("gin_first_party_infrastructure_evidence", "libgin", "doi_go_blob_sha1"), "0" * 40),
        (
            (
                "reviewed_upstream_evidence",
                "gin_history_evidence_fingerprint_sha256",
            ),
            "0" * 64,
        ),
        (
            (
                "reviewed_upstream_evidence",
                "gin_accessible_host_evidence_fingerprint_sha256",
            ),
            "0" * 64,
        ),
    ],
)
def test_rejects_refingerprinted_provenance_drift(
    path: tuple[str, ...], value: object
) -> None:
    record = _set_nested(_record(), path, value)
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_gin_rights_model_exhaustion(record)


def test_rejects_tampered_revalidated_author_body(tmp_path: Path) -> None:
    author = json.loads(AUTHOR.read_text(encoding="utf-8"))
    author["rights_interpretation"]["analysis_use_authorized"] = True
    tampered = tmp_path / "author.json"
    tampered.write_text(json.dumps(author), encoding="utf-8")
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_gin_rights_model_exhaustion(EVIDENCE, author_path=tampered)
