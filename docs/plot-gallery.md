---
tags:
  - Visualization
  - Plots
  - Diagnostics
  - Validation
---

# Plot gallery

A scientific figure should make the **interpretation boundary** visible as well as the result.

## Research lifecycle

![GazeForge research lifecycle](assets/figures/research-lifecycle.svg)

**Use for:** understanding where source preservation, QC, review, analysis, validation, and reporting sit.

**Do not infer:** that completing every stage establishes external or construct validity.

## QC diagnostics

![Synthetic gaze quality-control diagnostics](assets/figures/synthetic-qc-diagnostics.svg)

**Use for:** identifying quality patterns requiring interpretation or review.

**Do not infer:** that a QC flag is automatically an exclusion.

## Event diagnostics

![Synthetic event diagnostics](assets/figures/synthetic-event-diagnostics.svg)

**Use for:** inspecting event segmentation behaviour.

**Do not infer:** that a visually plausible threshold is universally valid.

## AOI scanpath

![Synthetic AOI scanpath](assets/figures/synthetic-aoi-scanpath.svg)

**Use for:** communicating reviewed spatial or semantic sequence structure.

**Do not infer:** latent cognitive states from sequence geometry alone.

## Dynamic AOIs

![Synthetic dynamic AOI example](assets/figures/synthetic-dynamic-aoi.svg)

![Reviewed temporal support and bounded interpolation for dynamic AOIs](assets/figures/dynamic-aoi-support.svg)

**Use for:** distinguishing reviewed temporal support from bounded interpolation.

**Do not infer:** that extrapolated boxes outside reviewed support are validated AOIs.

## Validation design

![Event validation workflow](assets/figures/event-validation-workflow.svg)

**Use for:** explaining why grouping and held-out unit identity belong in the validation claim.

## Benchmark evidence

### Lund2013 derived-60 evidence

![Lund2013 derived 60 Hz benchmark performance](assets/figures/lund2013-derived60-performance.svg)

### Hollywood2EM derived-60 evidence

![Hollywood2EM derived 60 Hz benchmark performance](assets/figures/hollywood2em-derived60-performance.svg)

**Do not infer:** that derived-rate evidence is equivalent to native-device evidence.

## Location-scale modelling

![Location-scale workflow](assets/figures/location-scale-workflow.svg)

Use with [hierarchical location-scale models](hierarchical-location-scale.md), [residual calibration](location-scale-residual-calibration.md), and [bootstrap Monte Carlo precision](location-scale-bootstrap-monte-carlo.md).
