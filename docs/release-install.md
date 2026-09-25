# Release & install

GazeForge has two deliberately different software surfaces: the **immutable published alpha** and the **current repository development tree**. Reproducible work should state which one was used.

## Current published artifact: `0.1.0a2`

GazeForge `0.1.0a2` is the current public alpha. It is published on PyPI through Trusted Publishing and frozen as an exact GitHub Release.

```bash
python -m pip install "gazeforge==0.1.0a2"
```

Optional extras in the published `0.1.0a2` artifact include:

```bash
python -m pip install "gazeforge[plot]==0.1.0a2"
python -m pip install "gazeforge[vision]==0.1.0a2"
```

Exact release identity:

- PyPI: `gazeforge==0.1.0a2`
- Git tag: `v0.1.0a2`
- GitHub Release: `https://github.com/stefanosbalaskas/GazeForge/releases/tag/v0.1.0a2`
- release commit: `cc2b74eb5f56bf7a1ab4c7db00c0f68eba5ee436`
- project DOI: `10.5281/zenodo.22650012`

The project DOI is persistent project-level citation metadata. For **exact byte identity**, preserve the package version/tag or the artifact hashes below.

```text
gazeforge-0.1.0a2-py3-none-any.whl  sha256:ff8bee1efacac7b36cccae6ecfed56dfd428d6c85e3b37263673321c1b6e8705
gazeforge-0.1.0a2.tar.gz            sha256:36f70467422ffd1879500c77415fbb38a95ae481f9f66f305b918ed0b7f425c7
```

The PyPI publication was produced from those exact GitHub Release distributions with Trusted Publishing and digital attestations.

### Historical `0.1.0a1`

The first public alpha remains part of the project's historical provenance. Its version-specific Zenodo DOI is `10.5281/zenodo.22650013`. Use that identifier only when reproducing or citing the first alpha itself, not as the current package version.

For manuscript-ready software and development citation guidance, use [Citation & attribution](citation-attribution.md).

## Current `main`: development software

After a release, `main` may contain newer documentation, tests, or APIs that are not part of the immutable `0.1.0a2` artifact. For repository work:

```bash
git clone https://github.com/stefanosbalaskas/GazeForge.git
cd GazeForge
python -m pip install -e ".[dev]"
pytest
```

For plotting in a development checkout:

```bash
python -m pip install -e ".[plot]"
```

Do not describe an unreleased `main` checkout only as “GazeForge 0.1.0a2” when the analysis depends on commits added after the release tag.

## Commit-pinned research

For a paper, preregistration, benchmark, or archived analysis that uses repository code after the release, pin the exact commit:

```bash
git clone https://github.com/stefanosbalaskas/GazeForge.git
cd GazeForge
git checkout <exact-commit-sha>
python -m pip install -e "."
```

Record the full commit SHA together with the environment, data fingerprints, model configuration, and applicable evidence/certificate fingerprints.

## Which surface should I use?

| Goal | Recommended surface |
| --- | --- |
| Reproduce the current public alpha exactly | `gazeforge==0.1.0a2` from PyPI |
| Verify immutable release bytes | `v0.1.0a2` GitHub Release + SHA-256 hashes |
| Reproduce the historical first alpha | `0.1.0a1` + version DOI `10.5281/zenodo.22650013` |
| Use newly developed APIs not yet released | commit-pinned repository checkout |
| Develop or contribute | editable `.[dev]` checkout |
| Generate current visual diagnostics | `gazeforge[plot]==0.1.0a2` or current checkout with `.[plot]` |
| Cite the software artifact | [Citation & attribution](citation-attribution.md) |
| Cite scientific validation strength | [Evidence status](evidence-status.md), not the package version alone |

## Release-state rule

A feature listed under **Unreleased** in the [changelog](changelog.md) belongs to repository development until a new immutable package release is published. Documentation on `main` may therefore become newer than `0.1.0a2`; this page separates release identity from development identity.
