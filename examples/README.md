# GazeForge examples

These scripts are intentionally small and deterministic. They are learning and smoke-test examples, not empirical validation artifacts.

Website gallery: [Runnable examples](../docs/runnable-examples.md)

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

## Reproducibility notes

The examples use fixed or explicitly constructed synthetic/demo inputs. For manuscript-facing work, record the GazeForge version or exact commit SHA and do not treat synthetic output as tracker validation or empirical evidence.
