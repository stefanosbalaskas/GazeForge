# Native event validation suite

The native event validation suite binds the three reports required for a defensible first-pass native-device evidence tranche:

1. **human-human agreement** between two explicitly named annotators;
2. **primary model-human validation** against the prespecified primary annotator;
3. **annotator-sensitivity model validation** against the second annotator.

The suite is orchestration and integrity infrastructure. It does **not** supply a native GP3 corpus and does not create a GP3-specific performance claim by itself.

## Why use a suite manifest

A folder containing one or two successful benchmark JSON files is not evidence that the complete validation programme finished. GazeForge therefore treats the suite manifest as the completion marker.

The runner follows this order:

1. preflight all intended output paths;
2. load and fingerprint the empirical data file and JSON specification;
3. compute human-human agreement in memory;
4. compute the primary-annotator model benchmark in memory;
5. compute the second-annotator sensitivity benchmark in memory;
6. verify every child report fingerprint;
7. verify that all children refer to the same source-file SHA-256 and specification fingerprint;
8. freeze the three child reports;
9. write `native-event-suite-manifest.json` **last**;
10. immediately revalidate the manifest and child reports.

If analysis fails before the three reports are ready, no completion manifest is created. If a write fails after one child has been written, the orphan child still does not constitute a complete suite because the manifest is absent.

## Run a complete native suite

A pixel-velocity example is:

```bash
gazeforge native-event-suite \
  expert-events.csv \
  native-gp3-spec.json \
  validation/native-gp3-v1 \
  --primary-annotator expert-a \
  --sensitivity-annotator expert-b \
  --event-min-iou 0.50 \
  --ivt-threshold-px-s 700 \
  --n-splits 5
```

When valid screen and viewing geometry are available, use an explicitly justified angular threshold instead:

```bash
gazeforge native-event-suite \
  expert-events.csv \
  native-gp3-spec.json \
  validation/native-gp3-v1 \
  --primary-annotator expert-a \
  --sensitivity-annotator expert-b \
  --ivt-threshold-deg-s 45 \
  --n-splits 5
```

The `45` value above is an example, not a GP3 default. Native validation continues to require exactly one explicit I-VT threshold choice.

## Frozen outputs

A completed suite contains exactly these child reports:

```text
native-human-agreement.json
native-primary-model.json
native-annotator-sensitivity-model.json
```

and one completion marker:

```text
native-event-suite-manifest.json
```

The manifest records the source data filename and SHA-256, specification filename and deterministic specification fingerprint, annotator roles, event-IoU threshold, model settings, participant split unit, explicit absence of resampling, child paths, every child report fingerprint, and the suite-level fingerprint.

The fixed three-report inventory is intentional. Additional exploratory or robustness analyses can exist beside the suite, but they cannot silently alter what `native-event-validation-v1` means.

## Verify a frozen suite

```bash
gazeforge native-event-suite-validate validation/native-gp3-v1
```

Full validation checks:

- suite identity and `status="complete"`;
- deterministic suite fingerprint;
- exact three-report inventory;
- unique, safe relative child paths;
- existence and JSON validity of each child;
- every child report fingerprint;
- source-file identity shared across all children;
- specification identity shared across all children.

For manifest-only structural validation:

```bash
gazeforge native-event-suite-validate \
  validation/native-gp3-v1 \
  --manifest-only
```

Manifest-only validation does not establish that child files are present or untampered. Use full validation before publication, review, or evidence deployment.

## Primary annotator versus sensitivity annotator

The role names are methodological bookkeeping. The primary annotator should be selected in the empirical protocol before final evaluation; the second annotator provides reference-sensitivity analysis. Human-human agreement is reported separately so disagreement between model and one annotator can be interpreted against observed human annotation variability.

The suite does not treat either annotator as infallible. Human-human event precision and recall remain bidirectional in the agreement child report.

## Evidence boundary

A suite can be called **complete** only when its completion manifest validates. A complete suite can be called **native empirical evidence** only when the underlying specification describes a real audited native dataset and passes all intake guardrails.

Accordingly, the repository's bundled native 60 Hz protocol template remains non-executable while `dataset_status` is `template`. Synthetic unit-test suites exercise software behavior only and must not be cited as tracker validation.

For the underlying data contract, native-rate verification, and individual report workflows, see [Native 60 Hz expert-event validation](native-60hz-validation.md).
