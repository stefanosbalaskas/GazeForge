from pathlib import Path

_PUBLIC_FILES = (Path("README.md"), Path("docs/index.md"))
_FORBIDDEN = (
    "two human dynamic-AOI annotators",
    "two dynamic-AOI annotators",
)
_REQUIRED = "one published curated dynamic-AOI annotation process involving two contributors"


def test_public_visus_copy_does_not_claim_two_independent_annotators():
    for path in _PUBLIC_FILES:
        text = path.read_text(encoding="utf-8")
        assert all(phrase not in text for phrase in _FORBIDDEN)
        assert _REQUIRED in text


def test_public_visus_copy_surfaces_bounded_unresolved_source_status():
    for path in _PUBLIC_FILES:
        text = path.read_text(encoding="utf-8")
        assert "Bounded empirical evidence" in text
        assert "full 25-participant × 11-stimulus benchmark is not recovered" in text
        assert "original source licensing remains unresolved" in text
        assert "native-GP3 claim" in text


def test_public_visus_copy_never_promotes_contributor_count_to_independence():
    for path in _PUBLIC_FILES:
        text = path.read_text(encoding="utf-8")
        assert _REQUIRED in text
        assert "no full-dataset model-validation, human-human-agreement" in text
