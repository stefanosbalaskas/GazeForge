from __future__ import annotations

import copy

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_model_reference_preflight import (
    build_gaze_in_wild_model_reference_preflight,
)


def _row(index: int, labeller: int, participant: int, trial: int) -> dict:
    n_samples = 100 + index
    return {
        "figshare_file_id": 20_000_000 + index,
        "name": f"PrIdx_{participant}_TrIdx_{trial}_Lbr_{labeller}.mat",
        "size_bytes": 10_000 + index,
        "md5": f"{index:032x}"[-32:],
        "sha256": f"{index:064x}"[-64:],
        "download_attempt": 1,
        "participant_token": f"PrIdx_{participant}",
        "trial_token": f"TrIdx_{trial}",
        "recording_token": f"PrIdx_{participant}_TrIdx_{trial}",
        "labeller_id": labeller,
        "process_filename": f"PrIdx_{participant}_TrIdx_{trial}.mat",
        "n_samples": n_samples,
        "timestamp_sha256_float64_le": f"{index + 1000:064x}"[-64:],
        "labels_sha256_int64_le": f"{index + 2000:064x}"[-64:],
        "inferred_sampling_rate_hz": 299.99,
        "label_code_counts": {"0": 10, "1": 40, "2": n_samples - 50},
        "filename_struct_labeller_agree": True,
        "raw_bytes_retained": False,
    }


def _probe() -> dict:
    rows: list[dict] = []
    index = 1
    # Labeller 1: 12 participants, 18 recordings.
    for participant in range(1, 13):
        rows.append(_row(index, 1, participant, 1))
        index += 1
    for participant in range(1, 7):
        rows.append(_row(index, 1, participant, 2))
        index += 1
    # Labeller 2: 11 participants, 20 recordings; participant breadth loses.
    for participant in range(20, 31):
        rows.append(_row(index, 2, participant, 1))
        index += 1
    for participant in range(20, 29):
        rows.append(_row(index, 2, participant, 2))
        index += 1
    # Labellers 5 and 6: six files each, filling the exact 50-file distribution fixture.
    for labeller, start in ((5, 40), (6, 50)):
        for participant in range(start, start + 6):
            rows.append(_row(index, labeller, participant, 1))
            index += 1
    assert len(rows) == 50
    return {
        "record_type": "gaze-in-wild-labeldata-hha-feasibility-probe-v1",
        "probe_fingerprint_sha256": "a" * 64,
        "source_binding": {
            "labeldata_article_id": 11673696,
            "exact_byte_reviewed_evidence_fingerprint_sha256": (
                "dbf277d698266fe53e337a15fc342e9af1835460d2bcc69c3992635de8fa0a00"
            ),
        },
        "verified_labeldata": {
            "file_count": 50,
            "total_size_bytes": 28_725_824,
            "all_files_matched_frozen_size_and_md5": True,
            "all_files_resolve_to_frozen_original_processdata": True,
            "all_raw_mat_bytes_deleted_after_inspection": True,
            "files": rows,
        },
        "scientific_boundary": {
            "exact_labeldata_bytes_reverified": True,
            "participant_disjoint_model_validation_created": False,
            "cross_dataset_validation_created": False,
            "gp3_validity_claim_created": False,
            "complete_file_to_publication_task_mapping_verified": False,
            "quarantine_exit_authorized": False,
            "new_empirical_performance_claim_created": False,
        },
        "raw_dataset_bytes_retained": False,
    }


def test_preflight_selects_participant_breadth_before_recording_count() -> None:
    record, result = build_gaze_in_wild_model_reference_preflight(_probe())
    assert result.selected_labeller_id == 1
    assert result.selected_participant_count == 12
    assert result.selected_recording_count == 18
    assert record["selection_policy"]["uses_model_performance_for_selection"] is False
    assert record["selection_policy"]["uses_label_frequencies_for_selection"] is False
    assert record["model_protocol_preregistration"]["task_mapping_used"] is False
    assert record["scientific_boundary"]["participant_disjoint_model_validation_created"] is False


def test_preflight_uses_lowest_labeller_id_only_after_coverage_tie() -> None:
    probe = _probe()
    files = probe["verified_labeldata"]["files"]
    labeller_one = [row for row in files if row["labeller_id"] == 1]
    labeller_two = [row for row in files if row["labeller_id"] == 2]
    for target, source in zip(labeller_two[:18], labeller_one, strict=True):
        participant = int(source["participant_token"].split("_")[1])
        trial = int(source["trial_token"].split("_")[1])
        index = target["figshare_file_id"] - 20_000_000
        replacement = _row(index, 2, participant, trial)
        target.clear()
        target.update(replacement)
    del labeller_two[18:]
    rebuilt = [row for row in files if row["labeller_id"] != 2] + labeller_two[:18]
    # Add two harmless labeller-6 rows to preserve the 50-row fixture.
    next_index = max(row["figshare_file_id"] for row in rebuilt) - 20_000_000 + 1
    rebuilt.append(_row(next_index, 6, 70, 1))
    rebuilt.append(_row(next_index + 1, 6, 71, 1))
    probe["verified_labeldata"]["files"] = rebuilt
    assert len(rebuilt) == 50
    _, result = build_gaze_in_wild_model_reference_preflight(probe)
    assert result.selected_labeller_id == 1


def test_label_frequency_changes_do_not_change_reference_selection() -> None:
    probe = _probe()
    _, baseline = build_gaze_in_wild_model_reference_preflight(probe)
    mutated = copy.deepcopy(probe)
    for row in mutated["verified_labeldata"]["files"]:
        if row["labeller_id"] == 2:
            n = row["n_samples"]
            row["label_code_counts"] = {"0": 1, "1": 1, "5": n - 2}
    _, changed = build_gaze_in_wild_model_reference_preflight(mutated)
    assert changed.selected_labeller_id == baseline.selected_labeller_id == 1


@pytest.mark.parametrize(
    "key",
    [
        "participant_disjoint_model_validation_created",
        "cross_dataset_validation_created",
        "gp3_validity_claim_created",
        "complete_file_to_publication_task_mapping_verified",
        "quarantine_exit_authorized",
        "new_empirical_performance_claim_created",
    ],
)
def test_preflight_rejects_promoted_parent_boundaries(key: str) -> None:
    probe = _probe()
    probe["scientific_boundary"][key] = True
    with pytest.raises(BenchmarkIntegrityError, match=key):
        build_gaze_in_wild_model_reference_preflight(probe)


def test_preflight_rejects_unknown_label_code() -> None:
    probe = _probe()
    row = probe["verified_labeldata"]["files"][0]
    row["label_code_counts"] = {"0": 10, "1": 40, "9": row["n_samples"] - 50}
    with pytest.raises(BenchmarkIntegrityError, match="unsupported label count"):
        build_gaze_in_wild_model_reference_preflight(probe)
