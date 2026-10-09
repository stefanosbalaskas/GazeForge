# Experimental multimodal pairing and reliability-weighted fusion

This research extension complements, rather than replaces, [validation-scope certificates](validation-scope-certificates.md) and [motion-quality gating](motion-quality-gating.md).

```python
from gazeforge.multimodal_integrity_research import (
    audit_temporal_session_separation,
    audit_multimodal_pairing,
    reliability_weighted_fusion,
)

split = audit_temporal_session_separation(train, test)
pairing = audit_multimodal_pairing({"gaze": gaze, "eda": eda})
# Only after independently checking clock alignment and making channel units comparable:
fusion = reliability_weighted_fusion(
    aligned_standardized,
    value_cols=("gaze_z", "eda_z"),
    weight_cols=("gaze_quality", "eda_quality"),
    values_are_commensurate=True,
)
```

## Scientific boundaries

- Split certification separately reports participant, session and temporal-block overlap from explicit IDs. Nonoverlapping named blocks do **not** prove independent time windows.
- Multimodal pairing can be `unpaired_cross_source`, `paired_within_person_not_trial`, or `paired_within_trial_not_time_certified`. It deliberately **never** certifies synchronized timestamps.
- Fusion computes a descriptive QC-weighted mean only after the caller explicitly certifies commensurate scales. It does **not** fit StressNet/HAFN, detect artifacts, prove higher prediction quality, or supply significance tests.
- No stable root namespace, frozen validation evidence, or release flags were changed.
- Scientific qualification requires artifact perturbation trials, weight-calibration assessments, and leakage-safe participant-disjoint prediction comparisons with equal-weight and complete-case baselines.

See [missingness assumptions](missing-data-assumptions.md) and [existing synthetic known-truth benchmarks](synthetic-known-truth-benchmarks.md).
