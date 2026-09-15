# Release & install

GazeForge has two deliberately different software surfaces: the **immutable published alpha** and the **current repository development tree**. Reproducible work should state which one was used.

## Published artifact: `0.1.0a1`

The first public alpha is published on PyPI and archived on Zenodo. Installing it gives the exact released artifact, not later capabilities added on `main`.

```bash
python -m pip install "gazeforge==0.1.0a1"
```

Release archive: `10.5281/zenodo.22650013`.

The GitHub Release distributions were identity-matched to the PyPI publication:

```text
gazeforge-0.1.0a1-py3-none-any.whl  sha256:3e409fbfc3c194db30ba25fefdf7f6459a3a003aefa0ab4303555d96982fbb46
gazeforge-0.1.0a1.tar.gz            sha256:cee4e061a90d74b3a354a0fb4aa5c7bd00d53577e17167f75342cd476a5c25fa
```

`0.1.0a1` predates later repository work such as the first-class visual-diagnostics layer. Do not infer that an optional extra visible in the current `pyproject.toml` exists in the already-published alpha.

## Current `main`: development software

For the latest repository capabilities, clone GazeForge and install the checkout in editable mode:

```bash
git clone https://github.com/stefanosbalaskas/GazeForge.git
cd GazeForge
python -m pip install -e ".[dev]"
pytest
```

Optional plotting support in the current development tree can be installed with:

```bash
python -m pip install -e ".[plot]"
```

This does **not** mean `gazeforge[plot]==0.1.0a1` was part of the immutable first alpha.

## Commit-pinned research

For a paper, preregistration, benchmark, or archived analysis, pin the exact repository commit rather than describing the software only as “latest GazeForge”:

```bash
git clone https://github.com/stefanosbalaskas/GazeForge.git
cd GazeForge
git checkout <exact-commit-sha>
python -m pip install -e "."
```

Record the commit SHA together with the analysis environment, data fingerprints, model configuration, and applicable GazeForge evidence/certificate fingerprints.

## Which surface should I use?

| Goal | Recommended surface |
| --- | --- |
| Reproduce the first public alpha exactly | `gazeforge==0.1.0a1` from PyPI |
| Use newly developed APIs not yet released | commit-pinned repository checkout |
| Develop or contribute | editable `.[dev]` checkout |
| Generate current visual diagnostics | current checkout with `.[plot]` |
| Cite scientific validation strength | [Evidence status](evidence-status.md), not the package version alone |

## Release-state rule

A feature listed under **Unreleased** in the [changelog](changelog.md) belongs to repository development until a new immutable package release is actually published and archived. Documentation for `main` may therefore describe APIs that are newer than `0.1.0a1`; this page is the boundary between those two claims.
