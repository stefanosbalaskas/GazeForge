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

This direct-loader example is appropriate for ingestion development. It is **not sufficient for a
participant-held-out or cross-dataset Hollywood2EM evidence artifact** because the callback itself
does not prove the source copy, reuse terms, coordinate basis, or identity mapping.

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

The low-level loader permits `coordinate_unit="pixels"` only as an explicit caller declaration. A
caller declaration is not, by itself, frozen scientific evidence. Before publication-grade
cross-dataset work, use the separate [Hollywood2EM source audit](hollywood2-source-audit.md), which
binds the coordinate claim to a reviewed verification basis and exact file manifest.

## Source-audit gate for stronger evidence

The repository provides `Hollywood2SourceAuditSpec`, `audit_hollywood2_source()`, and
`load_audited_hollywood2_directory()`. An empirical participant-aware audit requires exact ARFF
SHA-256/byte-size records, participant/trial identities, pinned source revision, reviewed reuse
terms, explicit analysis-use permission, coordinate-unit evidence, and participant-mapping
evidence. It also loads both human label streams and verifies that they refer to the same underlying
gaze samples.

The bundled `validation/protocols/hollywood2-source-audit-template.json` is intentionally
non-executable. It does **not** mean that participant identity, coordinate units, or redistribution
rights have been resolved.

## Reviewed source-token-held-out checkpoint

A narrower reviewed evidence tranche is already frozen. It is bound to the canonical GIN source
commit:

```text
870fa6d6209c9085260918d61433a0a2c70fd497
```

The reviewed preparation contains **450,649 derived-60-Hz analysis rows**, evaluated in **four
matched source-token-held-out folds** over **16 opaque canonical filename tokens**. Those tokens are
used only as disjoint source identifiers; they are **not claimed to be participants**.

Aggregate four-fold means are:

| Model | Accuracy | Macro-F1 | Event-F1 |
| --- | ---: | ---: | ---: |
| **I-VT** | 0.70149 | 0.56046 | **0.62856** |
| **RandomForest** | 0.75339 | 0.74038 | 0.43974 |
| **ContextMLP** | **0.81733** | **0.81194** | 0.60227 |

The result is deliberately multi-criterion. ContextMLP is strongest for the reported aggregate
sample-level summaries, while I-VT has the highest event-F1. This checkpoint does not support a
blanket superiority claim for any model.

The reviewed report fingerprint is:

```text
a7a6219d6ffcb1fc6622110887a95f2c9d0646fea6e22d0ada941fe07b90586a
```

The frozen-summary fingerprint is:

```text
e1f1c030f843e118ebd65520dfab8e872efb4ea3e1d520299a993b0ca00ddabf
```

### Scope boundary

This checkpoint establishes **source-token-disjoint aggregate derived-60-Hz evidence only**. It does
not establish participant-disjoint or stimulus-held-out validation, does not identify the 16 opaque
filename tokens as participants, and does not unlock Lund2013↔Hollywood2EM cross-dataset claims.
The exact annotation-repository licence text/identifier and the token→participant mapping remain
unresolved.

The student/final annotation relation is also sequential correction, not two independent human
annotation streams. Student-versus-final equality is therefore treated as annotation sensitivity,
not independent human-human agreement.

## Planned cross-dataset use

Hollywood2EM is **native 500 Hz**, not native 60 Hz. A GP3-class comparison must therefore be
reported as a derived lower-rate analysis if the data are resampled. The candidate cross-dataset
protocol harmonises Lund2013 and Hollywood2EM to 60 Hz with explicit label-purity rules and limits
the primary common event set to fixation, saccade, and pursuit.

That stronger analysis remains blocked until participant identity, coordinate interpretation, and
reuse provenance are resolved through the authoritative audit path. The reviewed source-token
checkpoint above does not satisfy those stronger gates.

## Distribution and claims

The accompanying article is openly licensed, but GazeForge does not infer that the raw dataset has
the same redistribution terms. The dataset remains external. The reviewed source-token checkpoint
is summary-only and non-redistributive: no raw source rows or predictions are committed. Its
operator authorization is not a legal or licensing determination.

Accordingly, GazeForge may report the reviewed source-token-disjoint aggregate checkpoint, but it
does **not** promote that checkpoint to participant-held-out, stimulus-held-out, cross-dataset,
native-60-Hz, GP3-specific, or unrestricted redistribution evidence.
