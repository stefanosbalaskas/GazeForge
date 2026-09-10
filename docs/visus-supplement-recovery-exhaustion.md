# VISUS 2021 supplementary-material recovery checkpoint

GazeForge freezes a reviewed negative-recovery checkpoint for the supplementary
event exports described by Barz and Sonntag's 2021 *Sensors* paper
(`10.3390/s21124143`). This checkpoint extends the
[VISUS source-resolution record](visus-source-resolution.md); it does not replace
the 2014 benchmark source-authority gate.

## Result

**No exact supplementary object or authoritative attachment URL was recovered
from the reviewed current and archived public surfaces.**

This is deliberately narrower than saying that the supplement never existed.
The 2021 paper explicitly states that extracted VISUS ground-truth events and
predicted events for each scenario and participant were provided as
supplementary material. The recovery result therefore records a present
evidentiary limitation, not a historical non-existence claim.

The frozen evidence file is:

```text
validation/evidence/visus-source-recheck/
visus-2021-supplement-recovery-exhaustion-evidence-v1.json
```

Canonical evidence fingerprint:

```text
6e263fe3c8ec202e06cd6c819be622bbe1831202b94393e2bea205df25278761
```

## Exact reconnaissance binding

The checkpoint binds the successful reconnaissance workflow rather than
transcribing an unqualified search conclusion:

- branch: `feat/visus-pmc-supplement-probe`;
- exact head: `347ba06dd802f9bd8b38aa2a6c770949702bc3ea`;
- workflow: `VISUS PMC supplement discovery`, run `34497168884` (run number 7);
- artifact: `visus-pmc-supplement-discovery`, artifact ID `10160434617`;
- artifact digest:
  `sha256:4545afdc8a37aee06b8415b68a7bc23614943fa6ac9dcbba774034fed3f7479d`.

The record also freezes the raw SHA-256 and internal deterministic fingerprint
of all six JSON probe reports in that artifact.

## What the reviewed surfaces establish

The exact PMC Open Access package for `PMC8235043` contains the article objects
and seven figure images but no object classified as supplementary material.
The exact PMC XML is 243,122 bytes with SHA-256
`2aa36a03effd0ffca21a72cd610a0efe9825d35709c88c20f62db14933b96bc5`
and contains PMC metadata whose supplement property is `no`. That describes the
current PMC package; it is **not** treated as proof that the publisher never
hosted a supplement.

Current MDPI article and `/s1` requests returned HTTP 403 in the reviewed run.
Those are access outcomes, not absence evidence.

A historically observed MDPI static-attachment naming convention was used only
to construct a bounded candidate set for `sensors-21-04143-s001` across twelve
common extensions. All twelve HEAD requests returned 404 and no binary target
resolved. Because the filename stem itself was inferred, those responses do
not establish the original supplement's name or format.

The corrected Wayback article-namespace queries each returned five ordinary
article captures and no supplement candidate. The final static
`mdpi-res.com/d_attachment/...` namespace queries timed out, so the record
explicitly keeps `complete_negative_search_established=false`.

Finally, the archived 2022 MDPI XML replay was successfully retrieved at
324,681 bytes. It contains the target DOI and supplement-related text but
exposes zero candidate supplement links. The 2021 archived HTML replay timed
out. Accordingly, both archived article captures were not successfully
inspected, and no historical attachment URL is promoted.

## Why this is a recovery-exhaustion checkpoint

The purpose of the record is to stop repeated blind URL enumeration after the
reviewed search reached diminishing scientific value. It preserves the exact
negative observations and their limitations so a future recovery attempt can
start from a new authoritative lead rather than repeat the same guesses.

The checkpoint therefore keeps all of the following false:

- supplement object recovered, URL resolved, bytes downloaded, or contents
  inspected;
- conclusion that the supplement never existed;
- claim that every possible public surface has been exhaustively proven
  negative;
- full authoritative VISUS source recovery or VISUS dataset licensing;
- analysis-use or raw-source redistribution rights;
- participant/stimulus mapping or annotation independence;
- human-human, model-human, cross-dataset, or native-60-Hz/GP3 validation;
- Frozen Evidence or any new empirical-performance claim;
- raw-source redistribution.

The 2021 article's CC BY 4.0 status is not projected onto the missing VISUS
benchmark files, and this checkpoint does not resolve reuse terms for an
unrecovered supplementary object.

## Remaining legitimate recovery routes

Future recovery should proceed only when there is a new authenticated lead:

1. recover an exact supplement object or explicit attachment URL from an
   authenticated MDPI, PMC, DOI-linked, or archival publisher surface;
2. obtain the 2021 supplementary archive or equivalent exact event exports
   from the paper authors, DFKI, or current VISUS custodians through a normal
   authorized channel;
3. use a current author/institutional redeposit that explicitly identifies the
   2021 event exports and states the applicable reuse terms.

Any recovered object must be source-authenticated, byte-fingerprinted, and
independently reviewed before it can affect source authority, rights, or
scientific validation.

## Validation

The fail-closed validator is:

```python
from gazeforge.visus_supplement_recovery_exhaustion import (
    validate_visus_supplement_recovery_exhaustion,
)

validate_visus_supplement_recovery_exhaustion(
    "validation/evidence/visus-source-recheck/"
    "visus-2021-supplement-recovery-exhaustion-evidence-v1.json"
)
```

The validator revalidates the already-frozen 2026-09-09 VISUS authoritative
source recheck, binds the exact successful reconnaissance artifact and all six
probe identities, and rejects refingerprinted attempts to widen any recovery,
rights, source-authority, empirical, or redistribution claim.

No VISUS roadmap checkbox is completed by this negative-recovery checkpoint.
