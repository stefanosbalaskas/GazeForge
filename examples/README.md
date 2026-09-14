# GazeForge examples

These scripts are intentionally small and deterministic. They are learning and smoke-test examples, not empirical validation artifacts.

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

## Reproducibility notes

The examples use fixed or explicitly constructed synthetic/demo inputs. For manuscript-facing work, record the GazeForge version or exact commit SHA and do not treat synthetic output as tracker validation or empirical evidence.
