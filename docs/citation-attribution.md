# Citation & attribution

GazeForge separates **software identity**, **development identity**, and **scientific evidence**. Cite the software artifact you actually ran, then record the evidence or benchmark provenance that supports any scientific-performance claim.

!!! important "Do not cite `main` as though it were the published alpha"
    The current immutable public alpha is `v0.1.0a2`. If an analysis uses commits added after that tag, record the exact Git commit and environment rather than implying those later bytes are part of the release.

## Choose the citation that matches your analysis

<div class="grid cards" markdown>

-   :material-package-variant-closed:{ .lg .middle } **Published `0.1.0a2`**

    ---

    Use `0.1.0a2` when your analysis actually used the current public alpha from PyPI or the matching GitHub Release.

    **Project DOI:** `10.5281/zenodo.22650012`

    **Exact release identity:** `v0.1.0a2` plus the published artifact hashes.

-   :material-source-commit:{ .lg .middle } **Commit-pinned development build**

    ---

    If you used capabilities added after `v0.1.0a2`, record the exact full Git commit and environment. Do not attach the release identity to later code as if it identified those bytes.

-   :material-shield-check-outline:{ .lg .middle } **Scientific evidence**

    ---

    Software citation does not establish validation strength. Record the applicable benchmark source, evidence class, report/certificate fingerprint, sampling provenance, and split semantics separately.

</div>

## Current published software: `0.1.0a2`

The second public alpha was frozen on **25 September 2026** at tag `v0.1.0a2` and published to PyPI through Trusted Publishing from the exact GitHub Release distributions.

A compact project citation is:

> Balaskas, S. (2026). *GazeForge: Auditable AI for Eye-Tracking Analysis* (Version 0.1.0a2) [Computer software]. https://doi.org/10.5281/zenodo.22650012

BibTeX:

```bibtex
@software{balaskas_gazeforge_2026,
  author  = {Balaskas, Stefanos},
  title   = {GazeForge: Auditable AI for Eye-Tracking Analysis},
  year    = {2026},
  version = {0.1.0a2},
  doi     = {10.5281/zenodo.22650012},
  url     = {https://doi.org/10.5281/zenodo.22650012},
  license = {MIT}
}
```

For exact artifact identity, also report:

- Git tag `v0.1.0a2`;
- release commit `cc2b74eb5f56bf7a1ab4c7db00c0f68eba5ee436`;
- wheel SHA-256 `ff8bee1efacac7b36cccae6ecfed56dfd428d6c85e3b37263673321c1b6e8705`; and
- source-distribution SHA-256 `36f70467422ffd1879500c77415fbb38a95ae481f9f66f305b918ed0b7f425c7`.

The DOI is project citation metadata; the version/tag/hash fields provide the byte-level release identity used for reproducible analysis.

Author identity: **Stefanos Balaskas**, University of Patras, ORCID [`0000-0003-2444-9796`](https://orcid.org/0000-0003-2444-9796).

The repository contains [`CITATION.cff`](https://github.com/stefanosbalaskas/GazeForge/blob/main/CITATION.cff), which exposes current citation metadata.

## Historical first alpha

GazeForge `0.1.0a1` remains immutable historical provenance. Its version-specific Zenodo DOI is [`10.5281/zenodo.22650013`](https://doi.org/10.5281/zenodo.22650013).

Use that DOI when reproducing or citing the **first alpha itself**. Do not use it to identify `0.1.0a2` or later repository code.

## Commit-pinned development use

Current documentation can describe APIs and evidence newer than `v0.1.0a2`. If your study used a repository checkout after the release, pin the exact commit:

```bash
git rev-parse HEAD
python --version
python -m pip freeze > environment.txt
```

Record at minimum:

| Field | What to report |
| --- | --- |
| Software | GazeForge |
| Release or repository | `0.1.0a2` / `v0.1.0a2`, or exact development commit |
| Commit | full 40-character Git SHA for development use |
| Python | exact interpreter version |
| Environment | locked/archived dependency set |
| Analysis inputs | dataset/file fingerprints where applicable |
| Evidence | applicable GazeForge report/certificate fingerprints |

A development methods statement can use this structure:

> Analyses used GazeForge from the project repository at Git commit `<40-character-SHA>`. The Python environment and analysis inputs were archived with the study materials. Scientific validation claims were restricted to the benchmark evidence and provenance reported for that commit.

Do not substitute “latest GazeForge” for the commit SHA in a reproducible research record.

## Cite software and evidence separately

A software identifier answers **which implementation did you run?** An evidence record answers **what empirical support exists for the claim you are making?** They are related but not interchangeable.

For empirical claims, pair software identity with the appropriate public evidence surface:

- [Evidence status](evidence-status.md) — canonical evidence class and boundary for each benchmark.
- [Frozen empirical evidence](frozen-evidence.md) — publication-gated frozen reports and provenance summaries.
- [Validation status](validation-status.md) — broader implementation and validation matrix.
- Benchmark-specific pages — source identity, sampling origin, split semantics, annotation/reference strength, and unresolved limitations.

When a report or certificate supplies a deterministic fingerprint, preserve it in the analysis record. A fingerprint is provenance, **not** a DOI and not a substitute for citing the original benchmark dataset or publication when that source has its own citation requirements.

## Evidence boundaries that belong in manuscripts

- Lund2013 lower-rate evidence is **derived 60 Hz from native 500 Hz data**, not native GP3 validation.
- Hollywood2EM source-token-disjoint evidence is **not participant-disjoint**.
- Gaze-in-the-Wild currently has reviewed participant-disjoint task-agnostic evidence, while the complete authoritative numeric task mapping remains unresolved.
- VISUS currently supports **bounded partial public-derivative empirical evidence**, not full-dataset VISUS validation or native-GP3 validity.
- Synthetic/demo outputs are examples and tests, not empirical validation evidence.

Use [Evidence status](evidence-status.md) rather than inferring validation strength from a package version, metric card, or screenshot.

## Software paper status

**There is currently no GazeForge software paper being claimed on this website.** Do not invent a journal citation or cite an unpublished manuscript as though it were an archival publication.

When a software paper is genuinely published, it can be added here as an **additional** citation for the project's design, methods, or scientific rationale. It should not replace citation of the exact software artifact used in an analysis.

### Software-paper readiness checklist

A future paper should be prepared only when its claims can be tied to a frozen, reproducible project state. At minimum:

- an immutable software release and persistent archive;
- stable citation metadata and author identity;
- explicit scientific-governance boundaries;
- reproducible examples and documentation;
- public validation/evidence surfaces with deterministic provenance;
- benchmark-specific rights/source boundaries that do not overstate redistribution or validation; and
- a frozen manuscript analysis environment and exact software/evidence identifiers.

## Recommended reporting bundle

For a paper, preregistration, registered report, or public analysis archive, preserve these together:

1. **Software identity** — release version/tag/hash or exact Git commit.
2. **Environment identity** — Python and dependency versions.
3. **Input identity** — dataset/source versions and file fingerprints where permitted.
4. **Model/configuration identity** — thresholds, random seeds, trained-model/configuration fingerprints where applicable.
5. **Evidence identity** — benchmark/report/certificate fingerprints and evaluation split semantics.
6. **Human-review provenance** — corrections, adjudication, exclusions, or AOI-review decisions where relevant.

This bundle preserves GazeForge's core rule: **AI-assisted analysis must remain auditable back to the empirical record.**

[Release & install →](release-install.md) · [Reproducible reporting →](reproducible-reporting.md) · [Scientific governance →](scientific-governance.md) · [Evidence status →](evidence-status.md)
