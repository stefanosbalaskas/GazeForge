---
tags:
  - Articles
  - Missing data
  - Censoring
  - Statistics
---

# Missing is not zero

Eye-tracking pipelines frequently create quantities that *look* numeric but have different observation states.

## Distinguish the states

**Observed zero** means the quantity was observable and its measured value was zero.

**Missing** means the value was expected but unavailable.

**Absent by design** means the quantity was not part of that observation's design or exposure.

**Undefined** means the mathematical quantity cannot be computed for that row.

**Right-censored latency** means the event was not observed before the observation window ended; it does not mean latency was zero.

## Why zero-filling is dangerous

Replacing these states with zero changes means, proportions, rates, event counts, exposure-adjusted summaries, and model likelihoods.

## Carry observation state into the handoff

Statistical analysis should receive the measurement, denominator or exposure, grouping identity, and missing/censoring state together.

## Continue

- [Denominator, exposure & censoring clinic](../denominator-exposure-censoring.md)
- [Missing-data assumptions](../missing-data-assumptions.md)
- [Analysis handoff](../analysis-handoff.md)
- [Grouping & repeated measures](../grouping-repeated-measures.md)
