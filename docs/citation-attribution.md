# Citation & attribution

GazeForge separates **software identity**, **development identity**, and **scientific evidence**. Cite the artifact you actually ran, then record the evidence or benchmark provenance that supports any scientific-performance claim.

!!! important "Do not cite `main` as though it were the published alpha"
    The Zenodo DOI below identifies the immutable `0.1.0a1` release. Features and evidence added later on `main` are not retroactively part of that archived artifact.

## Choose the citation that matches your analysis

<div class="grid cards" markdown>

-   :material-package-variant-closed:{ .lg .middle } **Published `0.1.0a1`**

    ---

    Use the version DOI when your analysis actually used the immutable public alpha.

    **Identifier:** `10.5281/zenodo.22650013`

-   :material-source-commit:{ .lg .middle } **Commit-pinned development build**

    ---

    If you used capabilities added after `0.1.0a1`, record the exact Git commit and environment. Do not attach the alpha DOI to later code as if it identified those bytes.

-   :material-shield-check-outline:{ .lg .middle } **Scientific evidence**

    ---

    Software citation does not establish validation strength. Record the applicable benchmark source, evidence class, report or certificate fingerprint, and sampling/split provenance separately.

</div>

## Published software: `0.1.0a1`

The first public alpha was released on **7 September 2026** and archived with the version-specific Zenodo DOI [`10.5281/zenodo.22650013`](https://doi.org/10.5281/zenodo.22650013).

A compact software citation is:

> Balaskas, S. (2026). *GazeForge: Auditable AI for Eye-Tracking Analysis* (Version 0.1.0a1) [Computer software]. https://doi.org/10.5281/zenodo.22650013

BibTeX:

```bibtex
@software{balaskas_gazeforge_2026,
  author  = {Balaskas, Stefanos},
  title   = {GazeForge: Auditable AI for Eye-Tracking Analysis},
  year    = {2026},
  version = {0.1.0a1},
  doi     = {10.5281/zenodo.22650013},
  url     = {https://doi.org/10.5281/zenodo.22650013},
  license = {MIT}
}
```

Author identity: **Stefanos Balaskas**, University of Patras, ORCID [`0000-0003-2444-9796`](https://orcid.org/0000-0003-2444-9796).

The repository also contains [`CITATION.cff`](https://github.com/stefanosbalaskas/GazeForge/blob/main/CITATION.cff), which GitHub can use to expose citation metadata. The release-specific `.zenodo.json` remains the metadata source used for the archived GitHub release and is intentionally not rewritten to describe later development.

## Commit-pinned development use

Current documentation can describe APIs and evidence newer than `0.1.0a1`. If your study used a repository checkout rather than the published alpha, pin the exact commit:

```bash
git rev-parse HEAD
python --version
python -m pip freeze > environment.txt
```

Record at minimum:

| Field | What to report |
| --- | --- |
| Software | GazeForge |
| Repository | `https://github.com/stefanosbalaskas/GazeForge` |
| Commit | full 40-character Git SHA |
| Python | exact interpreter version |
| Environment | locked/archived dependency set |
| Analysis inputs | dataset/file fingerprints where applicable |
| Evidence | applicable GazeForge report/certificate fingerprints |

A methods statement can use this structure:

> Analyses used GazeForge from the project repository at Git commit `<40-character-SHA>`. The Python environment and analysis inputs were archived with the study materials. Scientific validation claims were restricted to the benchmark evidence and provenance reported for that commit.

Do not substitute “latest GazeForge” for the commit SHA in a reproducible research record.

## Cite software and evidence separately

A software identifier answers **which implementation did you run?** An evidence record answers **what empirical support exists for the claim you are making?** They are related but not interchangeable.

For empirical claims, pair the software identity with the appropriate public evidence surface:

- [Evidence status](evidence-status.md) — canonical evidence class and boundary for each benchmark.
- [Frozen empirical evidence](frozen-evidence.md) — publication-gated frozen reports and provenance summaries.
- [Validation status](validation-status.md) — broader implementation and validation matrix.
- Benchmark-specific pages — source identity, sampling origin, split semantics, annotation/reference strength, and unresolved limitations.

When a GazeForge report or certificate supplies a deterministic fingerprint, preserve that fingerprint in the analysis record. A fingerprint is provenance, **not** a DOI and not a substitute for citing the original benchmark dataset or publication when that source has its own citation requirements.

## Evidence boundaries that belong in manuscripts

The citation layer must not erase scientific scope. In particular:

- Lund2013 lower-rate evidence is **derived 60 Hz from native 500 Hz data**, not native GP3 validation.
- Hollywood2EM source-token-disjoint evidence is **not participant-disjoint**.
- Gaze-in-the-Wild currently has reviewed participant-disjoint task-agnostic evidence, while the complete authoritative numeric task mapping remains unresolved.
- VISUS currently supports **bounded partial public-derivative empirical evidence**, not full-dataset VISUS validation or native-GP3 validity.
- Synthetic/demo outputs are examples and tests, not empirical validation evidence.

Use the [Evidence status](evidence-status.md) page as the current public boundary rather than inferring validation strength from a package version, metric card, or screenshot.

## Software paper status

**There is currently no GazeForge software paper being claimed on this website.** Do not invent a journal citation or cite an unpublished manuscript as though it were an archival publication.

When a software paper is genuinely published, it can be added here as an **additional** citation for the project’s design, methods, or scientific rationale. It should not replace the citation of the exact software artifact used in an analysis.

### Software-paper readiness checklist

A future paper should be prepared only when its claims can be tied to a frozen, reproducible project state. At minimum, that means:

- an immutable software release and persistent archive;
- stable citation metadata and author identity;
- explicit scientific-governance boundaries;
- reproducible examples and documentation;
- public validation/evidence surfaces with deterministic provenance;
- benchmark-specific rights/source boundaries that do not overstate redistribution or validation;
- a frozen manuscript analysis environment and exact software/evidence identifiers.

## Recommended reporting bundle

For a paper, preregistration, registered report, or public analysis archive, preserve these together:

1. **Software identity** — release DOI or exact Git commit.
2. **Environment identity** — Python and dependency versions.
3. **Input identity** — dataset/source versions and file fingerprints where permitted.
4. **Model/configuration identity** — thresholds, random seeds, trained-model/configuration fingerprints where applicable.
5. **Evidence identity** — benchmark/report/certificate fingerprints and evaluation split semantics.
6. **Human-review provenance** — corrections, adjudication, exclusions, or AOI-review decisions where relevant.

This bundle is more informative than citing the package name alone and preserves GazeForge’s core rule: **AI-assisted analysis must remain auditable back to the empirical record.**

[Release & install →](release-install.md) · [Reproducible reporting →](reproducible-reporting.md) · [Scientific governance →](scientific-governance.md) · [Evidence status →](evidence-status.md)
