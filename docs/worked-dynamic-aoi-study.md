# Worked dynamic-AOI study

This worked example shows how to analyze a moving stimulus when semantic regions change position over time. It uses deterministic **synthetic/demo fixation data and researcher-defined dynamic AOI keyframes** so every transformation is inspectable.

!!! warning "Software demonstration, not empirical validation"
    The bundle is classified `synthetic_demo_not_empirical_evidence`. It does not validate a detector, tracker, native 60 Hz acquisition, Gazepoint, GP3, or a substantive psychological effect.

## What the example demonstrates

The script `examples/05_worked_dynamic_aoi_study.py` creates three moving semantic tracks:

- `product`;
- `claim`; and
- `cta`.

Each track has reviewed keyframes at 0, 1000, and 2000 ms. Fixations between those times are mapped using **bounded linear interpolation** with an explicit `max_interpolation_gap_ms=1000.0`.

Two probe rows are deliberately placed outside the observed track range:

- `-100 ms`, before the first keyframe;
- `2100 ms`, after the last keyframe.

Those rows must remain unassigned. GazeForge does **not extrapolate** dynamic AOI geometry before the first or after the last observed keyframe.

## Run it

From a repository checkout with the plotting extra:

```bash
python -m pip install -e ".[plot]"
python examples/05_worked_dynamic_aoi_study.py \
  --output-dir worked-dynamic-aoi-demo
```

For the tables/provenance path without Matplotlib:

```bash
python examples/05_worked_dynamic_aoi_study.py \
  --output-dir worked-dynamic-aoi-demo \
  --no-figures
```

## Reviewable output bundle

The script writes exactly six CSV tables:

```text
01_source_fixations.csv
02_dynamic_aoi_keyframes.csv
03_fixation_dynamic_aoi_assignments.csv
04_semantic_scanpaths.csv
05_interpolation_audit.csv
06_assignment_summary.csv
```

It also writes:

```text
analysis_plan.json
provenance.json
workflow_manifest.json
```

When figures are enabled, it adds:

```text
figures/01_dynamic_aoi_snapshot.png
figures/02_dynamic_scanpath.png
```

### Why keep the interpolation audit?

`05_interpolation_audit.csv` makes temporal geometry resolution reviewable. It contains exact-keyframe timestamps, within-range interpolated timestamps, and the two out-of-range probes. A reviewer can therefore verify that:

- exact timestamps use the observed keyframe;
- within-range timestamps use `source="interpolated"`;
- gaps larger than the declared maximum would resolve to no geometry; and
- timestamps outside the observed track resolve to no geometry.

## Core API route

```python
from gazeforge import (
    DynamicAOIKeyframe,
    map_fixations_to_dynamic_aois,
    to_semantic_scanpaths,
)

keyframes = [
    DynamicAOIKeyframe("product", "product", 0.0, 200, 260, 600, 700),
    DynamicAOIKeyframe("product", "product", 1000.0, 350, 280, 750, 720),
]

assigned = map_fixations_to_dynamic_aois(
    fixations,
    keyframes,
    max_interpolation_gap_ms=1000.0,
    overlap_rule="highest_confidence",
)
scanpaths = to_semantic_scanpaths(assigned)
```

The example uses manually specified, reviewed demo keyframes. If a computer-vision model proposes keyframes in a real study, keep its model name/version, confidence, source, review decision, and any edited geometry. Proposal generation and scientific validity are separate questions.

## What the assignment table means

`03_fixation_dynamic_aoi_assignments.csv` keeps the original fixation columns and adds:

- `aoi_id`;
- `aoi_label`;
- `aoi_confidence`;
- `aoi_source`;
- `aoi_model_name`;
- `aoi_model_version`; and
- `aoi_geometry_timestamp_ms`.

A row with `aoi_source="interpolated"` means the geometry was resolved between two observed keyframes within the declared maximum gap. It does **not** mean the geometry was observed directly at that exact timestamp.

An unassigned row may mean there was no AOI at that location, no valid dynamic geometry at that time, or the fixation fell outside all candidate regions. Do not silently rewrite an unassigned result into a semantic label.

## Suggested real-study adaptation

For a real video or moving-interface study:

1. preserve the raw fixation/event export and the stimulus version;
2. record tracker, native sampling rate, observed timestamp cadence, display geometry, and synchronization method;
3. create or import timestamped dynamic AOI keyframes;
4. review AI-proposed tracks before scientific use;
5. predeclare the interpolation gap and overlap rule;
6. retain out-of-range and unresolved rows rather than extrapolating geometry;
7. generate fixation assignments and semantic scanpaths;
8. validate detector/tracker performance against suitable reference annotations if performance claims are made;
9. preserve participant/stimulus split identity when learned models are evaluated; and
10. freeze software identity, fingerprints, analysis parameters, and the scientific boundary.

Use the [Study-design templates](study-design-templates.md) for the records above.

## Claim-safe interpretation

Appropriate:

> Fixations were assigned to reviewed dynamic AOI tracks using bounded interpolation between timestamped keyframes; geometry was not extrapolated outside the observed track range.

Not appropriate:

> The model accurately tracked user attention throughout the video.

The second statement bundles several unsupported claims: detector accuracy, exhaustive tracking, and psychological interpretation.

Likewise, a fixation assigned to `cta` is evidence that the fixation centroid fell inside the CTA geometry at that timestamp. It does not by itself establish comprehension, persuasion, preference, intention, or causal influence.

## Next steps

- [Research recipes](research-recipes.md) for task-first workflow selection.
- [Dynamic AOIs](dynamic-aois.md) for the method contract.
- [Dynamic AOI evaluation](dynamic-aoi-evaluation.md) for empirical evaluation.
- [Study-design templates](study-design-templates.md) for preregistration and reporting records.
- [Publication readiness](publication-readiness.md) before a manuscript/archive freeze.
