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


def test_public_visus_copy_surfaces_unresolved_source_status():
    for path in _PUBLIC_FILES:
        text = path.read_text(encoding="utf-8")
        assert "empirical execution pending" in text
        assert "authoritative" in text
        assert "unresolved" in text


def test_public_visus_copy_never_promotes_contributor_count_to_independence():
    readme = Path("README.md").read_text(encoding="utf-8")
    homepage = Path("docs/index.md").read_text(encoding="utf-8")

    assert "contributor count is not treated as evidence of independent annotation streams" in readme
    assert "two contributors to one curation process are not treated as two independent" in homepage
