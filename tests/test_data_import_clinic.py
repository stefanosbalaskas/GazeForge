from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_real_data_clinic_is_first_class_learn_navigation() -> None:
    mkdocs = _read("mkdocs.yml")
    learn_start = mkdocs.index("  - Learn:\n")
    methods_start = mkdocs.index("  - Methods:\n", learn_start)
    learn_nav = mkdocs[learn_start:methods_start]

    learning_paths = "      - Learning paths: learning-paths.md"
    import_clinic = "      - Real-data import clinic: data-import-clinic.md"
    runnable = "      - Runnable examples: runnable-examples.md"

    assert learning_paths in learn_nav
    assert import_clinic in learn_nav
    assert runnable in learn_nav
    assert learn_nav.index(learning_paths) < learn_nav.index(import_clinic) < learn_nav.index(runnable)


def test_clinic_covers_all_supported_import_paths_and_public_helpers() -> None:
    guide = _read("docs/data-import-clinic.md")
    public_api = _read("src/gazeforge/__init__.py")

    for heading in (
        "Path A: Gazepoint / GP3 export",
        "Path B: generic processed table",
        "Path C: already-canonical table",
    ):
        assert heading in guide

    for helper in (
        "adapt_gazepoint_samples",
        "adapt_processed_table",
        "canonicalize_gaze",
        "infer_sampling_rate_hz",
        "fingerprint_frame",
        "ai_flag_anomalies",
        "score_trial_quality",
    ):
        assert helper in guide
        assert helper in public_api


def test_clinic_preserves_import_and_validation_boundaries() -> None:
    guide = _read("docs/data-import-clinic.md")

    assert "Import compatibility is not validation" in guide
    assert "does **not establish device validity**" in guide
    assert "does not establish native 60 Hz or GP3 event validity" in guide
    assert "does not silently repair, collapse, or delete duplicate timestamps" in guide
    assert "cadence diagnostic" in guide
    assert "not proof of the tracker's native/nominal hardware rate" in guide
    assert "Supplying a rate does not validate timestamps" in guide
    assert "do not clip them" in guide.lower()


def test_clinic_documents_units_identity_duplicates_geometry_and_qc() -> None:
    guide = _read("docs/data-import-clinic.md")

    for required in (
        "participant_id",
        "trial_id",
        "timestamp_ms",
        "x_px",
        "y_px",
        "time_unit=\"seconds\"",
        "coordinates=\"normalized\"",
        "timestamp_scale_to_ms=1000.0",
        "coordinate_scale=(width_px, height_px)",
        "duplicated(sample_key, keep=False)",
        "relative_difference",
        "source_fingerprint",
        "screen_size_px=gaze.screen_size_px",
        "Troubleshooting clinic",
    ):
        assert required in guide


def test_clinic_is_reachable_from_primary_learning_surfaces() -> None:
    for path in (
        "docs/index.md",
        "docs/getting-started.md",
        "docs/methods-overview.md",
        "docs/runnable-examples.md",
    ):
        text = _read(path)
        assert "data-import-clinic.md" in text, path
