import pytest

from scripts.hollywood2_author_license_probe import (
    GAZECOM_GIN_URL,
    HMD_GIN_URL,
    HOLLYWOOD2_GIN_URL,
    OPEN_LICENSE_PHRASE,
    build_probe_record,
)


def _text():
    return " ".join(
        [
            "Towards a better understanding of eye movements in natural contexts",
            "Ioannis Agtzidis",
            "Chapter 4 Hand-labeled data sets",
            OPEN_LICENSE_PHRASE,
            GAZECOM_GIN_URL,
            HOLLYWOOD2_GIN_URL,
            HMD_GIN_URL,
        ]
    )


def test_probe_records_statement_without_promoting_exact_rights():
    record = build_probe_record(
        pdf_bytes=b"%PDF synthetic fixture",
        extracted_text=_text(),
        final_url="https://mediatum.ub.tum.de/doc/1538004/1538004.pdf",
    )

    statement = record["observed_statement"]
    rights = record["rights_interpretation"]
    boundary = record["scientific_boundary"]
    assert statement["open_source_license_statement_present"] is True
    assert statement["hollywood2_gin_footnote_present"] is True
    assert rights["general_open_license_indication_verified"] is True
    assert rights["exact_license_identifier_recovered"] is False
    assert rights["exact_license_text_recovered"] is False
    assert rights["gin_analysis_use_terms_status"] == "unresolved_exact_terms"
    assert rights["gin_raw_data_redistribution_terms_status"] == "unresolved_exact_terms"
    assert boundary["exact_gin_dataset_license_verified"] is False
    assert boundary["gin_analysis_use_authorized"] is False
    assert boundary["gin_raw_data_redistribution_authorized"] is False
    assert boundary["source_audit_ready"] is False


def test_probe_refuses_missing_hollywood2_footnote():
    text = _text().replace(HOLLYWOOD2_GIN_URL, "")
    with pytest.raises(RuntimeError, match="hollywood2_gin_footnote_present"):
        build_probe_record(
            pdf_bytes=b"%PDF synthetic fixture",
            extracted_text=text,
            final_url="https://mediatum.ub.tum.de/doc/1538004/1538004.pdf",
        )


def test_probe_refuses_missing_open_license_statement():
    text = _text().replace(OPEN_LICENSE_PHRASE, "")
    with pytest.raises(RuntimeError, match="open_source_license_statement_present"):
        build_probe_record(
            pdf_bytes=b"%PDF synthetic fixture",
            extracted_text=text,
            final_url="https://mediatum.ub.tum.de/doc/1538004/1538004.pdf",
        )
