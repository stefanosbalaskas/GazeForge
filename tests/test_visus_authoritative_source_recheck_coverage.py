from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import gazeforge.visus_authoritative_source_recheck as recheck
from gazeforge.exceptions import BenchmarkIntegrityError

RECORD = Path(
    "validation/evidence/visus-source-recheck/visus-authoritative-source-recheck-2026-09-09.json"
)


def _payload() -> dict[str, Any]:
    return json.loads(RECORD.read_text(encoding="utf-8"))


def test_load_success() -> None:
    assert isinstance(
        recheck._load(RECORD),
        dict,
    )


def test_load_missing_guard(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load VISUS source recheck",
    ):
        recheck._load(tmp_path / "missing.json")


def test_load_invalid_json_guard(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bad.json"
    path.write_text(
        "{",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load VISUS source recheck",
    ):
        recheck._load(path)


def test_load_requires_object(
    tmp_path: Path,
) -> None:
    path = tmp_path / "array.json"
    path.write_text(
        "[]",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be a JSON object",
    ):
        recheck._load(path)


def test_require_mapping_success() -> None:
    value = {
        "section": {
            "x": 1,
        }
    }

    assert recheck._require_mapping(
        value,
        "section",
    ) == {
        "x": 1,
    }


def test_require_mapping_guard() -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be an object",
    ):
        recheck._require_mapping(
            {
                "section": [],
            },
            "section",
        )


def test_require_false_success() -> None:
    recheck._require_false(
        False,
        "fixture",
    )


@pytest.mark.parametrize(
    "value",
    [
        True,
        None,
        0,
        "",
    ],
)
def test_require_false_guard(
    value: Any,
) -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote fixture",
    ):
        recheck._require_false(
            value,
            "fixture",
        )


def test_require_true_success() -> None:
    recheck._require_true(
        True,
        "fixture",
    )


@pytest.mark.parametrize(
    "value",
    [
        False,
        None,
        1,
        "",
    ],
)
def test_require_true_guard(
    value: Any,
) -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must preserve fixture",
    ):
        recheck._require_true(
            value,
            "fixture",
        )


def test_authority_boundary_success() -> None:
    recheck._validate_authority_boundary(_payload())


def test_authority_boundary_mapping_guard() -> None:
    payload = _payload()
    payload["authoritative_source_recheck"] = []

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be an object",
    ):
        recheck._validate_authority_boundary(payload)


def test_authority_boundary_participant_count_guard() -> None:
    payload = _payload()

    payload["authoritative_source_recheck"]["full_expected_participant_count"] = 24

    with pytest.raises(
        BenchmarkIntegrityError,
        match="participant count must remain 25",
    ):
        recheck._validate_authority_boundary(payload)


def test_authority_boundary_stimulus_count_guard() -> None:
    payload = _payload()

    payload["authoritative_source_recheck"]["full_expected_stimulus_count"] = 10

    with pytest.raises(
        BenchmarkIntegrityError,
        match="stimulus count must remain 11",
    ):
        recheck._validate_authority_boundary(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "full_authoritative_corpus_recovered",
            True,
        ),
        (
            "current_institutional_publication_listing_found",
            False,
        ),
        (
            "current_authoritative_dataset_download_found",
            True,
        ),
        (
            "matching_darus_record_found",
            True,
        ),
        (
            "separate_dataset_doi_found",
            True,
        ),
        (
            "explicit_current_dataset_license_found",
            True,
        ),
        (
            "modern_darus_license_examples_not_transferable",
            False,
        ),
        (
            "partial_derivative_is_authoritative_replacement",
            True,
        ),
    ],
)
def test_authority_boundary_boolean_guards(
    field: str,
    value: bool,
) -> None:
    payload = _payload()

    payload["authoritative_source_recheck"][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
    ):
        recheck._validate_authority_boundary(payload)


def test_modern_darus_success() -> None:
    recheck._validate_modern_darus_examples(_payload())


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        [{}],
        [{}, {}, {}],
    ],
)
def test_modern_darus_shape_guard(
    value: Any,
) -> None:
    payload = _payload()
    payload["modern_darus_examples"] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="retain two bounded DaRUS examples",
    ):
        recheck._validate_modern_darus_examples(payload)


def test_modern_darus_row_mapping_guard() -> None:
    payload = _payload()

    payload["modern_darus_examples"][0] = "bad-row"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="DaRUS example must be an object",
    ):
        recheck._validate_modern_darus_examples(payload)


def test_modern_darus_applicability_guard() -> None:
    payload = _payload()

    payload["modern_darus_examples"][0]["applies_to_2014_benchmark"] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="modern DaRUS license",
    ):
        recheck._validate_modern_darus_examples(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "title",
            "wrong title",
        ),
        (
            "doi",
            "10.0000/wrong",
        ),
        (
            "license",
            "wrong license",
        ),
    ],
)
def test_modern_darus_frozen_identity_guard(
    field: str,
    value: str,
) -> None:
    payload = _payload()

    payload["modern_darus_examples"][0][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted from the frozen recheck",
    ):
        recheck._validate_modern_darus_examples(payload)


def _patch_derivative_validators(
    monkeypatch: pytest.MonkeyPatch,
    *,
    partial_fp: str | None = None,
    extension_fp: str | None = None,
) -> None:
    monkeypatch.setattr(
        recheck,
        "validate_visus_public_partial_evidence",
        lambda path: {
            "evidence_fingerprint_sha256": (
                partial_fp if partial_fp is not None else recheck.PUBLIC_PARTIAL_FINGERPRINT
            )
        },
    )

    monkeypatch.setattr(
        recheck,
        "validate_visus_public_event_extension_evidence",
        lambda path: {
            "evidence_fingerprint_sha256": (
                extension_fp if extension_fp is not None else recheck.EVENT_EXTENSION_FINGERPRINT
            )
        },
    )


def test_derivative_bindings_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_derivative_validators(monkeypatch)

    recheck._validate_derivative_bindings(
        _payload(),
        "partial.json",
        "extension.json",
    )


def test_derivative_partial_revalidation_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_derivative_validators(
        monkeypatch,
        partial_fp="0" * 64,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="public-partial evidence fingerprint drifted",
    ):
        recheck._validate_derivative_bindings(
            _payload(),
            "partial.json",
            "extension.json",
        )


def test_derivative_extension_revalidation_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_derivative_validators(
        monkeypatch,
        extension_fp="0" * 64,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="event-extension evidence fingerprint drifted",
    ):
        recheck._validate_derivative_bindings(
            _payload(),
            "partial.json",
            "extension.json",
        )


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        [{}],
        [{}, {}, {}],
    ],
)
def test_derivative_binding_shape_guard(
    monkeypatch: pytest.MonkeyPatch,
    value: Any,
) -> None:
    _patch_derivative_validators(monkeypatch)

    payload = _payload()
    payload["reviewed_derivative_evidence"] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="exactly two derivative records",
    ):
        recheck._validate_derivative_bindings(
            payload,
            "partial.json",
            "extension.json",
        )


def test_derivative_binding_row_mapping_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_derivative_validators(monkeypatch)

    payload = _payload()

    payload["reviewed_derivative_evidence"][0] = "bad-row"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="derivative binding must be an object",
    ):
        recheck._validate_derivative_bindings(
            payload,
            "partial.json",
            "extension.json",
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "full_visus_recovered",
            True,
        ),
        (
            "authoritative_replacement",
            True,
        ),
    ],
)
def test_derivative_binding_promotion_guards(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: bool,
) -> None:
    _patch_derivative_validators(monkeypatch)

    payload = _payload()

    payload["reviewed_derivative_evidence"][0][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
    ):
        recheck._validate_derivative_bindings(
            payload,
            "partial.json",
            "extension.json",
        )


def test_derivative_binding_record_identity_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_derivative_validators(monkeypatch)

    payload = _payload()

    payload["reviewed_derivative_evidence"][0]["record_type"] = "wrong"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="bindings drifted from reviewed records",
    ):
        recheck._validate_derivative_bindings(
            payload,
            "partial.json",
            "extension.json",
        )


def test_derivative_binding_fingerprint_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_derivative_validators(monkeypatch)

    payload = _payload()

    payload["reviewed_derivative_evidence"][0]["evidence_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="bindings drifted from reviewed records",
    ):
        recheck._validate_derivative_bindings(
            payload,
            "partial.json",
            "extension.json",
        )


def test_promotion_boundary_success() -> None:
    recheck._validate_promotion_boundary(_payload())


def test_promotion_boundary_mapping_guard() -> None:
    payload = _payload()
    payload["promotion_boundary"] = []

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be an object",
    ):
        recheck._validate_promotion_boundary(payload)


def test_promotion_boundary_exact_fields_guard() -> None:
    payload = _payload()

    payload["promotion_boundary"]["unexpected_flag"] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fields drifted",
    ):
        recheck._validate_promotion_boundary(payload)


@pytest.mark.parametrize(
    "field",
    recheck._EXPECTED_PROMOTION_FLAGS,
)
def test_promotion_boundary_false_guards(
    field: str,
) -> None:
    payload = _payload()

    payload["promotion_boundary"][field] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        recheck._validate_promotion_boundary(payload)


def test_top_level_date_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generic = {
        "record_type": "fixture",
        "checked_on": "2099-01-01",
        "status": "fixture",
        "record_fingerprint_sha256": (recheck.EXPECTED_RECORD_FINGERPRINT_SHA256),
    }

    monkeypatch.setattr(
        recheck,
        "validate_visus_source_resolution_record",
        lambda path: generic,
    )

    monkeypatch.setattr(
        recheck,
        "_load",
        lambda path: _payload(),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="recheck date drifted",
    ):
        recheck.validate_visus_authoritative_source_recheck("unused.json")


def test_top_level_fingerprint_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generic = {
        "record_type": "fixture",
        "checked_on": (recheck.EXPECTED_CHECKED_ON),
        "status": "fixture",
        "record_fingerprint_sha256": "0" * 64,
    }

    monkeypatch.setattr(
        recheck,
        "validate_visus_source_resolution_record",
        lambda path: generic,
    )

    monkeypatch.setattr(
        recheck,
        "_load",
        lambda path: _payload(),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="recheck fingerprint drifted",
    ):
        recheck.validate_visus_authoritative_source_recheck("unused.json")


def _patch_valid_top_level(
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, Any],
) -> None:
    generic = {
        "record_type": (payload["record_type"]),
        "checked_on": (recheck.EXPECTED_CHECKED_ON),
        "status": payload["status"],
        "record_fingerprint_sha256": (recheck.EXPECTED_RECORD_FINGERPRINT_SHA256),
    }

    monkeypatch.setattr(
        recheck,
        "validate_visus_source_resolution_record",
        lambda path: generic,
    )

    monkeypatch.setattr(
        recheck,
        "_load",
        lambda path: payload,
    )

    monkeypatch.setattr(
        recheck,
        "_validate_authority_boundary",
        lambda value: None,
    )

    monkeypatch.setattr(
        recheck,
        "_validate_modern_darus_examples",
        lambda value: None,
    )

    monkeypatch.setattr(
        recheck,
        "_validate_derivative_bindings",
        lambda *args: None,
    )

    monkeypatch.setattr(
        recheck,
        "_validate_promotion_boundary",
        lambda value: None,
    )


def test_top_level_annotation_mapping_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _payload()
    payload["annotation_independence"] = []

    _patch_valid_top_level(
        monkeypatch,
        payload,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be an object",
    ):
        recheck.validate_visus_authoritative_source_recheck("unused.json")


@pytest.mark.parametrize(
    "field",
    [
        "independent_annotation_streams_verified",
        "human_human_agreement_ready",
    ],
)
def test_top_level_annotation_promotion_guards(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    payload = _payload()

    payload["annotation_independence"][field] = True

    _patch_valid_top_level(
        monkeypatch,
        payload,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        recheck.validate_visus_authoritative_source_recheck("unused.json")


def test_frozen_record_success_again() -> None:
    result = recheck.validate_visus_authoritative_source_recheck(RECORD)

    assert result["record_fingerprint_sha256"] == recheck.EXPECTED_RECORD_FINGERPRINT_SHA256

    assert result["source_audit_authorized"] is False

    assert result["model_human_validation_authorized"] is False
