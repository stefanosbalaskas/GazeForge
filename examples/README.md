# GazeForge examples

These scripts are intentionally small and deterministic. They are learning and smoke-test examples, not empirical validation artifacts.

Website gallery: [Runnable examples](../docs/runnable-examples.md) · Task-first routes: [Research recipes](../docs/research-recipes.md)

## 1. Synthetic QC

```bash
python examples/01_synthetic_qc.py
```

This example uses the base installation to simulate gaze, canonicalise it, add non-destructive anomaly flags, and print trial-level quality summaries.

Guide: [Synthetic gaze to auditable QC](../docs/tutorial-synthetic-qc.md)

## 2. Transparent I-VT baseline

```bash
python examples/02_ivt_baseline.py
```

This base-install example applies the deterministic pixel-velocity I-VT baseline and prints class counts plus the event transitions in the first trial.

Guide: [Build an inspectable I-VT event baseline](../docs/tutorial-ivt-baseline.md)

## 3. Visual diagnostics

From a repository checkout, install the optional plotting layer and generate six synthetic/demo figures:

```bash
python -m pip install -e ".[plot]"
python examples/03_visual_diagnostics.py --output-dir visual-demo
```

The script demonstrates QC flags, event probabilities, calibration, semantic AOIs, scanpaths, and a bounded dynamic-AOI snapshot. It writes figure files only because it is an explicit example script; library plotting functions themselves never call `show()` or `savefig()`.

Guide: [Visual diagnostics](../docs/visual-diagnostics.md)

## 4. End-to-end research workflow

Run a complete reviewable composition of the public workflow layers:

```bash
python examples/end_to_end_research_workflow.py \
  --output-dir end-to-end-research-demo
```

The example writes source/canonical/QC/event/fixation/AOI/scanpath tables, operation provenance, a workflow manifest, fingerprints, and optional diagnostic figures. It verifies that the original source table remains unchanged and records the bundle as `synthetic_demo_not_empirical_evidence`.

For the analysis/export path without Matplotlib figures:

```bash
python examples/end_to_end_research_workflow.py \
  --output-dir end-to-end-research-demo \
  --no-figures
```

Guide: [Practical end-to-end research workflow](../docs/practical-workflow.md)

## 5. Worked advertising / interface study

Run a domain-shaped static-stimulus example with explicit `brand`, `claim`, `disclosure`, and `product` AOIs:

```bash
python examples/04_worked_advertising_study.py \
  --output-dir worked-advertising-demo
```

The script writes ten study-shaped CSV tables plus `analysis_plan.json`, `provenance.json`, and `workflow_manifest.json`. It verifies source immutability, records fingerprints, and labels the bundle `synthetic_demo_not_empirical_evidence`. The outputs illustrate software workflow and reporting structure; they are not empirical estimates of consumer behaviour or tracker validity.

Guide: [Worked advertising / interface study](../docs/worked-advertising-study.md) · [Study lifecycle](../docs/study-lifecycle.md)

## 6. Worked dynamic-AOI study

Run a moving-stimulus example that makes temporal AOI geometry and interpolation policy explicit:

```bash
python -m pip install -e ".[plot]"
python examples/05_worked_dynamic_aoi_study.py \
  --output-dir worked-dynamic-aoi-demo
```

For the table/provenance path without Matplotlib:

```bash
python examples/05_worked_dynamic_aoi_study.py \
  --output-dir worked-dynamic-aoi-demo \
  --no-figures
```

The script writes six CSV tables plus `analysis_plan.json`, `provenance.json`, and `workflow_manifest.json`. It exercises exact keyframes and bounded interpolation, deliberately includes pre/post-track fixation probes, verifies that geometry is **not extrapolated** outside the observed track range, checks source immutability, and labels the bundle `synthetic_demo_not_empirical_evidence`.

With figures enabled it also writes a dynamic-AOI snapshot and semantic scanpath figure. The outputs demonstrate software workflow and audit structure; they do not validate detector accuracy, tracker validity, native 60 Hz acquisition, Gazepoint/GP3, or substantive psychological effects.

Guide: [Worked dynamic-AOI study](../docs/worked-dynamic-aoi-study.md) · [Study-design templates](../docs/study-design-templates.md)

## 7. Worked event-model validation study

Run a participant-held-out model-comparison example that keeps split identity, sample/event metrics, probabilities, calibration, and confidence/coverage visible:

```bash
python -m pip install -e ".[plot]"
python examples/06_worked_event_model_validation.py \
  --output-dir worked-event-model-validation-demo
```

For the tables/provenance path without Matplotlib:

```bash
python examples/06_worked_event_model_validation.py \
  --output-dir worked-event-model-validation-demo \
  --no-figures
```

The script compares I-VT, Random Forest, and ContextMLP on identical four-fold **participant-disjoint** test rows. It writes the synthetic labelled source, participant split ledger, matched held-out predictions, separate sample-level and event-level metric tables, model summary, calibration bins, confidence/coverage diagnostics, an illustrative abstention-policy table, `analysis_plan.json`, `provenance.json`, and `workflow_manifest.json`.

It mechanically verifies zero participant overlap between training and test sets, checks that each model sees the same held-out rows, preserves probabilities/model identity, checks source immutability, and labels the bundle `synthetic_demo_not_empirical_evidence`. The 0.80 abstention threshold is an explicit teaching policy for the demo—not a universal confidence cutoff. Synthetic model ordering is not evidence of general model superiority, benchmark performance, native 60 Hz validity, Gazepoint validity, or GP3 validity.

With figures enabled it additionally writes `figures/01_calibration.png` and `figures/02_confidence_coverage.png`.

Guide: [Event-model validation clinic](../docs/event-model-validation-clinic.md) · [Validation reporting cookbook](../docs/validation-reporting-cookbook.md)

## 8. Worked tracker import + QC

Run the import/QC example when you want to see a Gazepoint-style source table transformed into canonical milliseconds/pixels without hiding review cases:

```bash
python examples/07_worked_tracker_import_qc.py \
  --output-dir worked-tracker-import-qc-demo
```

The example uses explicit `USER_FILE`, `MEDIA_ID`, `TIME`, `BPOGX`, and `BPOGY` mappings, declares `TIME` as seconds and gaze coordinates as normalized screen fractions, and converts them to canonical milliseconds and pixels with a declared 1920 × 1080 screen. It deliberately retains a duplicate sample key, off-screen rows, and a missing gaze coordinate so the preflight/QC path demonstrates review rather than silent repair.

It writes five CSV tables—source export, canonical gaze, import preflight, QC samples, and trial quality—plus `import_contract.json`, `analysis_plan.json`, `provenance.json`, and `workflow_manifest.json`. The script verifies that the source table is unchanged and row counts are preserved through QC.

The nominal 60 Hz value and observed timestamp cadence are stored separately. Their agreement in this deterministic teaching example is not proof of native hardware cadence. The bundle is `synthetic_demo_not_empirical_evidence`; successful adapter execution is not Gazepoint/GP3, native-60-Hz, event-model, or measurement validation.

Guide: [Worked tracker import and QC](../docs/worked-tracker-import.md) · [Real-data import clinic](../docs/data-import-clinic.md)

## Reproducibility notes

The eight examples use fixed or explicitly constructed synthetic/demo inputs. For manuscript-facing work, record the GazeForge version or exact commit SHA and do not treat synthetic output as tracker validation or empirical evidence. Use the [Study-design templates](../docs/study-design-templates.md) while planning, the [Worked tracker import](../docs/worked-tracker-import.md) for import/QC handoff, the [Event-model validation clinic](../docs/event-model-validation-clinic.md) for learned event evaluation, and the [Publication readiness](../docs/publication-readiness.md) checklist before freezing a study bundle.
