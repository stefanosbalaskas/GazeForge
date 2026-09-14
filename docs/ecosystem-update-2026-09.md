# Ecosystem update — September 2026

## Related modelling addition elsewhere in the suite

The related **gpbiometricspy** package now includes a fully exact-main-certified crossed participant–item Gaussian hierarchical location–scale model with **one location random slope for each crossed factor**.

This note does **not** change GazeForge's AI/event-modelling evidence, frozen benchmark results, device-validity boundaries, release status or scientific claims. GazeForge remains focused on auditable AI for gaze events, semantic AOIs, scanpaths, validation and provenance. The gpbiometricspy addition is a separate statistical modelling path for continuous repeated outcomes after defensible measurement and event construction.

### Certification record

Certified gpbiometricspy PR #129 is pinned to merge SHA `d078e0366ace49c3ebeb2f6800bad6394d70631e`:

- 14/14 exact-main push workflow families green;
- 12/12 Ubuntu/macOS/Windows × Python 3.11–3.14 test lanes green;
- 782/782 tests;
- 14,015/14,015 statements;
- 6,757/6,776 raw branches = 99.7196%;
- 19 unchanged audited structural arcs with 0 unexpected, 0 stale and 0 unaudited debt;
- frozen `gpbiometrics 2.0.0` parity unchanged at 406/406.

[Read the crossed participant–item random-slope guide](https://stefanosbalaskas.github.io/gpbiometricspy/methods/crossed-random-slopes-location-scale/)

[Open gpbiometricspy PR #129](https://github.com/stefanosbalaskas/gpbiometricspy/pull/129)

The new random slopes estimate conditional-association heterogeneity. They are not event classifiers, artifact detectors, device-validity evidence, causal effects, or latent psychological-state estimates.
