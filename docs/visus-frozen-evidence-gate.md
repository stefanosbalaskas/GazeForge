# VISUS Frozen Evidence bundle gate

A completed VISUS validation suite is not, by itself, sufficient for publication in GazeForge's Frozen Evidence layer. The bundle gate requires the suite to be paired with the raw-execution provenance manifest produced by the guarded VISUS execution workflow.

The Python entry point is:

```python
from gazeforge.visus_evidence import validate_visus_frozen_evidence_bundle

summary = validate_visus_frozen_evidence_bundle("path/to/visus-suite")
```

## Required bundle

One directory must contain both:

- `visus-dynamic-aoi-suite-manifest.json`;
- `visus-execution-provenance.json`.

The suite validator reopens and verifies every required child report. The execution-provenance validator reopens the sibling suite again and verifies the exact source/intake/grid/suite binding. The bundle gate then cross-checks the suite fingerprint, report count, exact four-input execution contract, and source-audit/spec/manifest identity.

A successful result has `status="verified-bundle"` and `frozen_evidence_eligible_for_scientific_review=true`.

## What eligibility means

Eligibility is intentionally narrower than empirical validity. It means that the artifacts satisfy the integrity contract required before a VISUS result can be considered for the public evidence layer. It does **not** mean that GazeForge has independently established that:

- a local VISUS copy is authoritative;
- analysis or redistribution rights exist beyond the reviewed source-audit evidence;
- a human reference stream is ground truth;
- the historical two-contributor curation process represents two independent annotation streams;
- detector/tracker performance is scientifically adequate;
- model-emission frames can serve as the evaluation timestamp grid.

Those claims remain governed by the source audit, independent-stream gate, external timestamp-grid requirement, model-human validation report, and scientific review.

## Why this is separate from suite completion

Suite completion proves that the expected child artifacts were computed, frozen, fingerprinted, and mutually consistent. Execution provenance additionally binds those artifacts to the exact reviewed raw files supplied at execution time. Requiring both prevents a structurally valid suite from being promoted into Frozen Evidence without the raw-execution chain that produced it.

The gate is therefore a publication-control layer: **suite integrity + execution provenance are necessary for evidence review, but neither substitutes for empirical source verification or scientific interpretation.**
