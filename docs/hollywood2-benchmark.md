# Hollywood2 manual-event benchmark

GazeForge includes a conservative adapter for the manually labelled **Hollywood2EM** event data
introduced by Agtzidis, Startsev, and Dorr. The benchmark is useful as an external human-reference
corpus because it contains expert-corrected sample labels for fixation, saccade, smooth pursuit,
and noise during naturalistic movie viewing.

## What the adapter assumes

The adapter follows the public evaluation parser used for the benchmark:

- ARFF input files contain `time`, `x`, `y`, and `confidence`;
- `time` is stored in microseconds and is converted to GazeForge `timestamp_ms`;
- `(x, y) == (0, 0)` is treated as tracking loss for coordinate validity;
- `handlabeller_1` is the first/student annotation pass;
- `handlabeller_final` is the expert-corrected reference;
- the expected acquisition rate is 500 Hz unless the caller explicitly changes the guardrail;
- the public ARFF schema establishes screen-coordinate fields but does not, by itself, prove the
  post-processing unit used for `x`/`y`. The loader therefore marks coordinates as `unverified` by
  default even though they occupy the canonical `x_px`/`y_px` aliases.

Noise remains an explicit reference class. GazeForge does not collapse it into fixation or silently
discard it during ingestion.

## Participant identity is never guessed

The externally published parser preserves relative ARFF paths but does not define a filename grammar
that GazeForge can safely treat as participant identity. `load_hollywood2_directory()` therefore
uses the sentinel `__unresolved__` participant ID unless the caller supplies an audited
`identity_parser`.

This is intentional. Participant-held-out or cross-dataset validation should fail or remain blocked
until participant identities are mapped from the authoritative local dataset structure. Treating
one file as one participant could leak the same observer across train/test clips.

```python
from pathlib import Path
from gazeforge import load_hollywood2_directory


def identity(relative: Path) -> tuple[str, str]:
    # Replace this example with the mapping verified against your local dataset copy.
    participant, trial = relative.stem.split("_", maxsplit=1)
    return participant, trial


gaze = load_hollywood2_directory(
    "/path/to/hollywood2_em",
    annotator="final",
    identity_parser=identity,
)
```

## Coordinate-unit gate

Unit-sensitive event features must not be compared across datasets until the Hollywood2 coordinate
interpretation has been audited against the authoritative local data/source documentation. The
loader therefore defaults to:

```python
gaze = load_hollywood2_directory(
    "/path/to/hollywood2_em",
    identity_parser=identity,
    coordinate_unit="unverified",
)
```

After an external audit establishes that the ARFF values are pixels, the caller can make that
assumption explicit with `coordinate_unit="pixels"`. Cross-dataset benchmark preparation refuses
unverified coordinates by default. This separates *ingestion* from *scientific comparability*.

## Planned cross-dataset use

Hollywood2EM is **native 500 Hz**, not native 60 Hz. A GP3-class comparison must therefore be
reported as a derived lower-rate analysis if the data are resampled. The candidate cross-dataset
protocol harmonises Lund2013 and Hollywood2EM to 60 Hz with explicit label-purity rules and limits
the primary common event set to fixation, saccade, and pursuit.

The final/student annotation difference is a separate sensitivity analysis and must not be mixed
with model-generalisation metrics.

## Distribution and claims

The accompanying article is openly licensed, but GazeForge does not infer that the raw dataset has
the same redistribution terms. The dataset remains external. No frozen Hollywood2 result should be
published from GazeForge until the authoritative local data copy, participant mapping, and dataset
reuse terms have been checked.
