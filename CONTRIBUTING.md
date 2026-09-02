# Contributing to GazeForge

GazeForge welcomes reproducible contributions to eye-tracking analysis, validation, and research
software infrastructure.

## Development setup

```bash
git clone https://github.com/stefanosbalaskas/GazeForge.git
cd GazeForge
python -m pip install -e ".[dev]"
ruff check src tests
pytest
```

Documentation changes can be checked with:

```bash
python -m pip install -e ".[docs]"
mkdocs build --strict
```

## Scientific contribution requirements

Changes that introduce or materially alter learned models should include:

- a clear task definition and intended use;
- model/version metadata and a model card;
- sampling-rate assumptions where relevant;
- leakage-safe train/test or cross-validation design;
- deterministic/classical baselines where feasible;
- calibration or uncertainty diagnostics for probabilistic outputs;
- tests showing that raw empirical rows are not silently deleted or rewritten; and
- limitations and failure cases.

Synthetic tests are implementation evidence, not scientific validation. Claims of accuracy or
cross-domain generalisation require a documented benchmark dataset and frozen validation report.

## Scope

GazeForge is designed for observable eye-tracking outcomes and methodological research. Pull
requests that add diagnosis, personality, protected-trait, or unsupported latent mental-state
inference from gaze are out of scope.

## Pull requests

Keep changes focused. Add or update tests and documentation with the code. Explain scientific
assumptions, validation design, and any compatibility implications in the pull-request body.
