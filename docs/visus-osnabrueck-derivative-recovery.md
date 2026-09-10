# VISUS Osnabrück derivative recovery

GazeForge freezes a reviewed recovery checkpoint for the historical University of
Osnabrück multimedia-container conversion of the Kurzhals et al. VISUS benchmark.
This checkpoint follows the [VISUS source-resolution](visus-source-resolution.md)
and [2021 supplementary-material recovery](visus-supplement-recovery-exhaustion.md)
records. It materially improves the recoverable empirical structure while preserving
the unresolved authority and rights gates around the original benchmark.

## Result

A historical institutional derivative containing the **11 standard VISUS scenarios
and 25 participant gaze tracks per scenario was structurally recovered and
verified**.

This is not the same claim as recovering a current authoritative copy of the
original VISUS distribution.

The frozen record is:

```text
validation/evidence/visus-source-recheck/
visus-osnabrueck-derivative-recovery-evidence-v1.json
```

Canonical evidence fingerprint:

```text
78b538ad35e411fe9e7020d47c759d2d6d246c96887bf76da979e23f35335d32
```

## Institutional source

The Osnabrück Institute of Cognitive Science page for its multimedia-container
work explicitly lists the **Kurzhals et al. [K] dataset — 11 videos** among its
converted eye-tracking datasets and offers ASS and USF versions. The page states
that the converted datasets are provided for research purposes and requests
citation of both the converter work and the corresponding original dataset.

The reviewed bundle endpoint is:

```text
https://w3o.ikw.uni-osnabrueck.de/media/cv/mm_mkv/Kurzhals.zip
```

The legacy host currently presents an invalid TLS certificate chain. GazeForge's
reconnaissance therefore records that TLS verification did **not** succeed and
that retrieval required the runner's explicitly bounded insecure-TLS mode. That
retrieval fact is never promoted into source authority.

The server returned a real ZIP object with:

- remote size: `2,598,730,485` bytes;
- ZIP central-directory entries: `26`;
- USF MKV entries: `13`;
- ASS MKV entries: `13`;
- standard USF scenarios: `11`;
- two additional USF polygon variants for K1 and K2;
- two corresponding ASS polygon variants.

Only the ZIP metadata and selected members were inspected. Source bytes were not
committed to GazeForge and were not uploaded as workflow artifacts.

## Exact reconnaissance binding

The evidence record binds the successful temporary reconnaissance rather than
relying on a narrative transcription:

- branch: `research/visus-osnabrueck-derivative-probe`;
- exact head: `f4d614f67e519a90aa8326f562fac2be9772e825`;
- workflow: `VISUS Osnabrueck derivative recovery probe`;
- run: `34504772669` (run number 6), conclusion `success`;
- artifact: `visus-osnabrueck-derivative-probe`, ID `10163474159`;
- artifact digest:
  `sha256:f4b40d146cc7cd17478da6bb2752ce7f80028f62bbf6356dd9ffc5ab6d048e76`.

The artifact contains four compact JSON probe reports. Their raw byte counts and
SHA-256 hashes are frozen in the evidence record. Recovered MKV or ZIP source
bytes are absent from the artifact.

## Why USF matters

Schöning et al., *Visual Analytics of Gaze Data with Standard Multimedia
Players* (`10.16910/jemr.10.5.4`), describe the USF-based representation as
encapsulating complete gaze metadata without loss, whereas the ASS conversion
retains only selected metadata for visualization.

That publication-level statement makes USF the scientifically preferable
recovery candidate. GazeForge nevertheless keeps
`converter_transform_fidelity_independently_proven_for_this_archive=false`
because the recovered USF files have not been compared byte-for-byte or
field-for-field with an authoritative copy of the original VISUS exports.

The JEMR article's `CC BY 4.0` license covers the article. It is not projected
onto the converted VISUS dataset files.

## Eleven-scenario structural recovery

The workflow reconstructed each of the 11 standard USF members independently
from exact byte ranges of the 2.6 GB ZIP. For every member it verified the ZIP
local-header metadata, decompressed size, CRC-32, compressed SHA-256, inflated
SHA-256, Matroska/EBML signature, media stream properties, participant-track
identity, and AOI-track structure. Each reconstructed member was deleted from
the ephemeral runner after inspection.

All eleven scenarios passed the following common checks:

- exactly 25 participant tracks with participant numbers `1..25`;
- group suffix distribution `A=13`, `B=12`;
- participant payloads contain gaze, fixation, timestamp, and point metadata;
- video resolution `1920 × 1080`;
- average frame rate `25/1` fps;
- ZIP CRC verification;
- valid Matroska EBML identity.

The standard USF set totals `1,288,160,237` compressed bytes and
`1,305,649,112` inflated bytes.

| Scenario | USF member | AOIs recovered |
| --- | --- | --- |
| K1 | `01-car pursuit_usf.mkv` | Red Car; White Car |
| K2 | `02-turning car_usf.mkv` | Red Car |
| K3 | `03-dialog_usf.mkv` | Left Face; Right Face; Shirt |
| K4 | `04-thimblerig_usf.mkv` | Cup2; Cup1; Cup3 |
| K5 | `05-memory_usf.mkv` | Cards |
| K6 | `06-UNO_usf.mkv` | Left Hand; Right Hand; Stack Covered; Stack Uncovered |
| K7 | `07-kite_usf.mkv` | Person; Kite |
| K8 | `08-case exchange_usf.mkv` | Persons; Textbox; Case; Suspects |
| K9 | `09-ball game_usf.mkv` | Ball; Player White; Player Red1; Player Red2; Player Red3 |
| K10 | `10-bag search_usf.mkv` | Red Bag; Yellow Bag; Blue Bag; Red-White Bag; Personen; Brown Bag |
| K11 | `11-person search_usf.mkv` | Hooded; Red Shirt and Hat; Persons |

Every scenario has its own immutable structural fingerprint in the evidence
record. Each fingerprint binds its compressed/inflated file identities, video
properties, exact participant roster and group counts, aggregate participant
payload manifest, AOI titles, and aggregate AOI payload manifest.

## What this establishes

This tranche establishes a substantially stronger derivative-source fact than
the earlier small public fragments: a historical university-hosted conversion
of all 11 standard VISUS scenarios is still recoverable, and its internal
structure contains the expected 25-participant gaze corpus on every scenario.
The recovered resolution, frame rate, participant cardinality, A/B suffix
structure, and gaze metadata are consistent with the published benchmark.

This is sufficient to freeze the **derivative recovery and structural identity**
of the inspected files. It is not sufficient to promote the original-source
authority gate.

## What remains unresolved

The following remain explicitly false:

- current authoritative original VISUS copy recovered;
- exact identity to the original VISUS files;
- original VISUS dataset license resolved;
- analysis-use rights resolved;
- raw-source redistribution rights resolved;
- insecure legacy-host retrieval as authority evidence;
- identity of derivative AOI payloads to the original ViPER XML annotations;
- independent human annotation streams verified;
- VISUS source-audit authorization;
- human-human or model-human validation authorization;
- cross-dataset or native-60-Hz/GP3 validity authorization;
- empirical Frozen Evidence authorization;
- raw-source redistribution;
- any new empirical performance claim.

The source page's phrase “provided for research purposes” is preserved as an
important distribution-intent fact, but is not rewritten as a formal dataset
license. Similarly, the converter publication's article license is not treated
as a license for the converted dataset.

## AOI identity caution

The USF files contain semantically named rectangular AOI tracks. Some recovered
track titles are not textually identical to labels shown in the 2014 benchmark
paper figures. Therefore structural recovery of AOI streams does not prove that
the converter representation is a field-identical transformation of the
original ViPER XML annotations.

This distinction matters for model-human validation: GazeForge will not silently
substitute a derivative AOI stream for an authoritative original annotation
without explicit review.

## Participant-group caution

The participant tracks preserve `P#A`/`P#B` suffixes with 13 A and 12 B tracks
per scenario. These suffixes are retained as provenance. They are not interpreted
as different task conditions for every scenario; the original study used
scenario-specific task differences only where documented.

## Validation

The fail-closed validator is:

```python
from gazeforge.visus_osnabrueck_derivative_recovery import (
    validate_visus_osnabrueck_derivative_recovery,
)

validate_visus_osnabrueck_derivative_recovery(
    "validation/evidence/visus-source-recheck/"
    "visus-osnabrueck-derivative-recovery-evidence-v1.json"
)
```

The validator revalidates both the existing authoritative-source recheck and the
2021 supplement-recovery checkpoint, hard-binds the exact reconnaissance
run/artifact and all four report hashes, recomputes every scenario structural
fingerprint, and rejects refingerprinted attempts to promote authority, rights,
annotation independence, empirical validation, or redistribution.

## Next source-resolution step

The next legitimate promotion route is now narrower and better defined:

1. obtain an author/current-custodian-verified original VISUS copy or an
   authoritative redeposit tied to the 2014 benchmark;
2. resolve analysis-use and redistribution rights for that exact source copy;
3. compare its videos, gaze exports, and AOI annotations against the recovered
   Osnabrück USF derivative;
4. only if that comparison and rights review succeed, construct the reviewed
   source-audit certificate and open empirical execution.

Until then, the Osnabrück recovery is frozen as **strong derivative evidence**,
not as a substitute for the current authoritative source.
