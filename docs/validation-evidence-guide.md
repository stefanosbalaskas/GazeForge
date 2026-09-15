# Validation & evidence guide

GazeForge exposes several validation surfaces because **implementation, empirical evidence, source identity, and reproducibility answer different questions**. This page is a routing layer; it does not create a new evidence class or replace the generated evidence records.

!!! important "Canonical evidence status"
    [Evidence status](evidence-status.md) is the canonical public status layer. If wording on this guide ever conflicts with that generated page, use the generated evidence status and its bound provenance.

## Start from your question

<div class="grid cards" markdown>

-   :material-shield-check-outline:{ .lg .middle } **What empirical evidence exists now?**

    ---

    Start with the generated evidence classes and benchmark-specific boundaries.

    [Evidence status →](evidence-status.md)

-   :material-hammer-wrench:{ .lg .middle } **Is a capability implemented?**

    ---

    Check software/validation readiness without treating implementation as empirical validity.

    [Validation status →](validation-status.md)

-   :material-snowflake-check:{ .lg .middle } **Which reports are frozen?**

    ---

    Inspect publication-gated empirical reports, fingerprints, and provenance summaries.

    [Frozen empirical evidence →](frozen-evidence.md)

-   :material-radar:{ .lg .middle } **Is native 60 Hz / GP3 validated?**

    ---

    Keep native-device evidence separate from lower-rate conditions derived from higher-rate corpora.

    [Native 60 Hz validation →](native-60hz-validation.md) · [Empirical execution →](empirical-execution.md)

-   :material-source-branch-check:{ .lg .middle } **Where did the evidence come from?**

    ---

    Follow source-resolution state, authority, rights, and exact-byte provenance before making stronger claims.

    [Source-resolution status →](source-resolution-status.md)

-   :material-certificate-outline:{ .lg .middle } **What scope was actually certified?**

    ---

    Use scope certificates to preserve dataset, split, rate, annotation, and execution boundaries.

    [Validation scope certificates →](validation-scope-certificates.md)

-   :material-chart-box-outline:{ .lg .middle } **Which benchmark should I inspect?**

    ---

    Enter the benchmark documentation by research question rather than by internal file name.

    [Benchmark guide →](benchmark-guide.md)

-   :material-file-document-check-outline:{ .lg .middle } **How should I report or cite it?**

    ---

    Record exact software identity separately from the empirical evidence that supports a scientific claim.

    [Reproducible reporting →](reproducible-reporting.md) · [Citation & attribution →](citation-attribution.md)

</div>

## What can I claim?

| Research question | Start here | Do not infer |
| --- | --- | --- |
| What is the current evidence class for a benchmark? | [Evidence status](evidence-status.md) | implementation status ≠ empirical evidence |
| Is a method or workflow implemented and tested? | [Validation status](validation-status.md) | implemented ≠ externally validated |
| Is a report publication-gated and fingerprinted? | [Frozen empirical evidence](frozen-evidence.md) | reviewed/bounded evidence ≠ Frozen evidence |
| Does evidence establish native 60 Hz / GP3 validity? | [Native 60 Hz validation](native-60hz-validation.md) | derived 60 Hz ≠ native-device validation |
| Is the underlying source identity/authority resolved? | [Source-resolution status](source-resolution-status.md) | recovery candidate ≠ authoritative source |
| Can another researcher reconstruct the software/evidence state? | [Citation & attribution](citation-attribution.md) | a DOI or package version alone ≠ validation strength |

## Boundaries that must survive navigation

Routing should make evidence easier to find, not stronger than it is.

- **Lund2013:** lower-rate evidence is derived from native 500 Hz expert-labelled data; it is not native GP3/60 Hz validation.
- **Hollywood2EM:** source-token-disjoint evidence is not participant-disjoint.
- **Gaze-in-the-Wild:** current participant-disjoint evidence is task-agnostic; the complete authoritative numeric task mapping remains unresolved.
- **VISUS:** current evidence is bounded partial public-derivative evidence; it does not establish full VISUS model validation, Frozen Evidence, or native GP3 validity.
- **Synthetic/demo outputs:** examples and known-truth tests are not empirical benchmark evidence.

For the current machine-readable/public classification of those states, return to [Evidence status](evidence-status.md).

## If the answer is "not yet"

Open evidence gaps are documented rather than hidden:

- [Empirical execution](empirical-execution.md) tracks work that requires real empirical execution.
- [Native event validation suite](native-event-suite.md) defines the native-event validation surface.
- [Source-resolution status](source-resolution-status.md) records unresolved source/provenance gates.
- Benchmark-specific source-resolution pages document why stronger claims may remain blocked.

This guide intentionally avoids copying headline metric values. Use [Results gallery](results-gallery.md) for readable figures and [Frozen empirical evidence](frozen-evidence.md) for the validated report-level record.
