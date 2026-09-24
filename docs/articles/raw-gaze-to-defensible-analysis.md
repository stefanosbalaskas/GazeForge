---
tags:
  - Articles
  - Workflow
  - Provenance
  - QC
---

# From raw gaze to a defensible analysis

A gaze file becoming a dataframe is the **start** of an analysis, not evidence that the measurement is understood.

## Preserve source identity

Keep the source export, tracker or acquisition identity, participant/session/trial identifiers, timestamp representation, coordinate basis, geometry, nominal sampling rate, and observed timestamp cadence explicit.

A parser that can read a file establishes compatibility. It does not establish device validity, calibration quality, or scientific suitability.

## Canonicalise without erasing provenance

A canonical schema should make downstream analysis easier while retaining enough information to reconstruct what was transformed. Unit conversion, coordinate conversion, duplicate handling, timestamp repair, and sample-rate assumptions should therefore be explicit.

## Treat QC as evidence

Missingness, discontinuity, extreme velocity, geometry violations, and sampling irregularity can be measured. Those diagnostics should remain attached to the data rather than becoming hidden deletion rules.

## Separate review from exclusion

A QC rule can identify observations requiring review. The decision to retain or exclude belongs in a separate ledger with the reason, decision level, denominator impact, and whether the rule was prespecified.

## Derive events and AOIs after the measurement contract is clear

Fixations, saccades, dynamic AOIs, semantic assignments, and scanpaths depend on sampling, geometry, detector definitions, stimulus support, and review status.

![GazeForge lifecycle](../assets/figures/research-lifecycle.svg)

## Preserve the inferential unit

Samples, fixations, trials, stimuli, AOIs, and participants are not interchangeable independent observations. Before statistical modelling, preserve the grouping structure required by the design.

## Report the evidence class you actually have

Reproducible code, a successful parser, a synthetic benchmark, held-out dataset evidence, native-device validation, and construct validity answer different questions.

**A defensible analysis makes visible what was observed, transformed, reviewed, modelled, and still uncertain.**

## Related routes

- [Worked tracker import](../worked-tracker-import.md)
- [QC review & exclusion ledger](../qc-review-exclusion-ledger.md)
- [Analysis handoff](../analysis-handoff.md)
- [Scientific governance](../scientific-governance.md)
- [Research evidence bundle](../research-evidence-bundle.md)
