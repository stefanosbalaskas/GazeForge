---
tags:
  - Articles
  - Reporting
  - Reproducibility
  - Provenance
---

# From output to reviewer-ready evidence

A reviewer needs more than a table of final estimates. The evidence package should show how the result was obtained and what can be rerun.

## Freeze identity

Record the exact source inputs, preprocessing specification, event/AOI definitions, quality rules, model specification, software version, and random seed where applicable.

## Separate primary and sensitivity analyses

A primary result should remain distinguishable from alternative thresholds, detector settings, exclusion rules, or model specifications explored for robustness.

## Preserve diagnostic artifacts

Convergence information, residual diagnostics, calibration evidence, sampling-sensitivity results, and denominator changes belong in the evidence package when they affect interpretation.

## Write bounded reporting language

The Methods section should describe what was done. The Results section should describe what was observed. Limitations should identify the evidence boundary rather than converting missing validation into implied certainty.

## Reviewer handoff

A strong bundle lets a reviewer locate the source identity, rerun the core analysis, inspect the diagnostics, and understand which scientific claims are and are not supported.

## Continue

- [Research evidence bundle](../research-evidence-bundle.md)
- [Reporting clinic](../reporting-clinic.md)
- [Reviewer & replication handoff](../reviewer-replication-handoff.md)
- [Publication readiness](../publication-readiness.md)
