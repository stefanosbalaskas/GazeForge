# GazeForge examples

These scripts are intentionally small, deterministic, and runnable with the base GazeForge installation. They are learning and smoke-test examples, not empirical validation artifacts.

## 1. Synthetic QC

```bash
python examples/01_synthetic_qc.py
```

This example simulates gaze, canonicalises it, adds non-destructive anomaly flags, and prints trial-level quality summaries.

Guide: [Synthetic gaze to auditable QC](../docs/tutorial-synthetic-qc.md)

## 2. Transparent I-VT baseline

```bash
python examples/02_ivt_baseline.py
```

This example applies the deterministic pixel-velocity I-VT baseline and prints class counts plus the event transitions in the first trial.

Guide: [Build an inspectable I-VT event baseline](../docs/tutorial-ivt-baseline.md)

## Reproducibility notes

Both examples use fixed random seeds. For manuscript-facing work, record the GazeForge version or exact commit SHA and do not treat synthetic output as tracker validation or empirical evidence.
