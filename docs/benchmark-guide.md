# Benchmark guide

GazeForge uses multiple external benchmarks because no single dataset answers every validation question. This page helps you choose **which evidence trail to inspect** without ranking datasets or treating unlike sampling, annotation, split, and source conditions as interchangeable.

!!! important "Check the canonical status before citing a benchmark"
    The current evidence class and scientific boundary for each benchmark are generated on [Evidence status](evidence-status.md). This guide routes you to the right documentation; it does not promote evidence strength.

## Choose a benchmark

<div class="grid cards" markdown>

-   :material-eye-check-outline:{ .lg .middle } **Lund2013**

    ---

    Start here for paired expert event labels, participant-held-out event modelling, and sampling/purity sensitivity. Lower-rate analyses are **derived from native 500 Hz data** and are not native GP3 validation.

    [Lund2013 overview →](lund2013-benchmark.md) · [Sampling sensitivity →](lund-sensitivity.md)

-   :material-movie-open-outline:{ .lg .middle } **Hollywood2EM**

    ---

    Start here for expert-corrected event annotations and source-token-held-out evidence. Current source-token-disjoint evidence is **not participant-disjoint**, so participant-level generalisation must not be inferred.

    [Hollywood2EM benchmark →](hollywood2-benchmark.md) · [Source resolution →](hollywood2-source-resolution.md)

-   :material-earth:{ .lg .middle } **Gaze-in-the-Wild**

    ---

    Start here for reviewed participant-disjoint, task-agnostic event evidence and the associated source/task provenance trail. The complete authoritative numeric task mapping remains unresolved.

    [Gaze-in-the-Wild benchmark →](gaze-in-wild-benchmark.md) · [Source resolution →](gaze-in-wild-source-resolution.md)

-   :material-vector-polygon:{ .lg .middle } **VISUS**

    ---

    Start here for the current bounded partial public-derivative 60 Hz evidence and dynamic-AOI/source-recovery work. Do not treat it as full-dataset VISUS validation or native GP3 validity.

    [VISUS public partial evidence →](visus-public-partial-evidence.md) · [Source resolution →](visus-source-resolution.md)

</div>

## Choose by validation question

| If your question is… | Start with | Why |
| --- | --- | --- |
| How do event methods behave under controlled lower-rate derivation? | [Lund2013](lund2013-benchmark.md) | expert labels plus explicit native/derived-rate separation |
| What does the source-token-held-out Hollywood2EM evidence support? | [Hollywood2EM](hollywood2-benchmark.md) | preserves the non-participant-disjoint split boundary |
| Where is participant-disjoint task-agnostic event evidence available? | [Gaze-in-the-Wild](gaze-in-wild-benchmark.md) | participant-disjoint evidence with task-mapping limits kept visible |
| What empirical VISUS-derived material is publicly verified today? | [VISUS public partial evidence](visus-public-partial-evidence.md) | bounded public-derivative evidence without full-benchmark promotion |
| Does any benchmark establish native 60 Hz / GP3 validity? | [Native 60 Hz validation](native-60hz-validation.md) | derived/external conditions must not substitute for native-device evidence |
| Which benchmark results are publication-gated? | [Frozen empirical evidence](frozen-evidence.md) | report fingerprints and publication gates are shown explicitly |
| Which source/rights questions remain unresolved? | [Source-resolution status](source-resolution-status.md) | central routing to benchmark-specific provenance work |

## Comparison rules

Before comparing numbers across benchmark pages:

1. confirm the **reference annotation** is comparable;
2. confirm the **split unit** (participant, source token, or another unit);
3. separate **native acquisition rate**, processed-stream rate, and any **derived analysis grid**;
4. check whether the result is Frozen, Reviewed, Bounded, pending, or another current status on [Evidence status](evidence-status.md);
5. preserve source/rights limitations rather than treating data availability as proof of authority.

A larger metric from a different benchmark design is not automatically stronger evidence. GazeForge therefore keeps benchmark-specific provenance beside the result instead of publishing a single cross-dataset league table.

## Continue

- [Validation & evidence guide →](validation-evidence-guide.md)
- [Results gallery →](results-gallery.md)
- [Frozen empirical evidence →](frozen-evidence.md)
- [For researchers →](for-researchers.md)
- [Citation & attribution →](citation-attribution.md)
