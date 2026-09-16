# Research terminology and claim boundaries

Small wording differences can imply very different evidence. Use this guide to keep acquisition provenance, split identity, software behaviour, validation, and substantive interpretation distinct.

## Acquisition and rate

| Term | Use it when | It does **not** mean |
| --- | --- | --- |
| **Native sampling rate** | samples were acquired by the device under that rate/configuration | a higher-rate corpus was later resampled to this rate |
| **Derived sampling rate** | a lower/different-rate condition was constructed from another acquired stream | native-device evidence at the derived rate |
| **Observed timestamp cadence** | rate/cadence is estimated from positive within-trial timestamp intervals | proof of the device's configured nominal rate |

**Appropriate:** “The 60 Hz condition was derived from the native 500 Hz expert-labelled corpus.”

**Avoid:** “The tracker/model was validated at native 60 Hz” when the analysed condition was resampled from higher-rate data.

## Split identity

| Split label | What is disjoint | Claim boundary |
| --- | --- | --- |
| **Participant-disjoint** | participants do not cross train/test partitions | requires authoritative participant identity |
| **Stimulus-disjoint** | stimuli/items do not cross partitions | does not guarantee participant disjointness |
| **Source-token-disjoint** | opaque source tokens do not cross partitions | must not be promoted to participant-disjoint without a verified mapping |
| **Dataset-held-out** | an entire dataset/source domain is held out | tests cross-dataset transfer, not every form of population generalisation |

Write the actual split unit. “Held out” by itself is incomplete.

## Import, QC, and validity

| Distinction | Meaning |
| --- | --- |
| **Import compatibility** | documented columns/units can be transformed into the canonical schema |
| **Device validity** | empirical evidence supports measurement/model validity for a device/acquisition setting |
| **QC/anomaly flag** | a row or trial is unusual under a defined rule/model and should be reviewed |
| **Invalid sample** | a scientific/technical decision has classified the sample as unusable under a justified rule |

A successful `adapt_gazepoint_samples()` call establishes a software transformation contract. It does not establish Gazepoint/GP3 event accuracy or native 60 Hz validity.

## AOIs and review

| Term | Meaning |
| --- | --- |
| **Researcher-defined/manual AOI** | geometry/label is specified directly by the research design |
| **AI-proposed AOI** | a model generated a candidate label/region with provenance/confidence |
| **Human-reviewed AOI** | a researcher explicitly accepted, rejected, relabelled, or corrected a proposal |
| **Frozen AOI** | the final geometry/labels used for manuscript-facing analysis are fixed and traceable |

AI confidence is not human ground truth. Preserve the proposal and the review decision as separate records.

## Sample-level and event-level performance

**Sample-level classification** asks whether individual time samples receive the correct class. Typical summaries include balanced accuracy and macro-F1.

**Event-level temporal performance** asks whether contiguous events are detected with appropriate onset, offset, overlap, and segmentation. Typical summaries include event-F1, temporal IoU, and boundary error.

A model can rank differently under these estimands. Do not describe the sample-level winner as the universal “best event detector.”

## Calibration and correctness

A **calibrated probability** means predicted confidence corresponds reasonably to observed frequency on suitable held-out data. It does not mean each individual prediction is correct.

Use calibration metrics such as ECE or Brier score when the claim concerns confidence reliability, and report discrimination/event metrics separately.

## Demo evidence and empirical evidence

A **software demo** is an example used to illustrate software behaviour, workflow composition, plotting, provenance, regression testing, or reporting structure. A software demo is not empirical validation evidence.

| Label | Appropriate interpretation |
| --- | --- |
| **Synthetic/demo output** | software behaviour, workflow composition, plotting, provenance, regression testing |
| **Empirical validation evidence** | performance/evidence derived from an appropriate empirical reference design with explicit provenance and scope |

The bundled examples use the classification `synthetic_demo_not_empirical_evidence`. They are useful precisely because they make software behaviour inspectable without pretending to validate a tracker or scientific effect.

## Provenance and validation

A **fingerprint/checksum** identifies exact bytes or a deterministic table representation. It helps answer “what was analysed?”

A **validation result** answers a different question: “how well did this method perform under a specified empirical reference design?”

Do not treat a reproducible file identity as evidence that the file, labels, device, or model are scientifically valid.

## Observable gaze measures and latent interpretation

Gaze data can directly support descriptions such as:

- where a fixation was assigned;
- when an event occurred;
- how long a region was inspected;
- in what sequence semantic AOIs were visited;
- what confidence a model emitted; and
- how outputs behaved under a stated validation design.

Those observations do not, by themselves, establish emotion, liking, persuasion, deception, comprehension, diagnosis, personality, purchase intention, or another latent construct. Stronger interpretation requires an independent theoretical and empirical bridge.

## Quick wording substitutions

| Avoid | Prefer |
| --- | --- |
| “validated at 60 Hz” | “evaluated on a derived 60 Hz condition from native 500 Hz data” |
| “participant-held-out” when identity is opaque | “source-token-disjoint” |
| “invalid samples were detected by AI” | “samples were flagged for review by the anomaly procedure” |
| “AI identified the true AOIs” | “AI proposed AOIs that were subsequently reviewed” |
| “best event detector” | “highest macro-F1 under this sample-level evaluation” or the relevant estimand |
| “the model was 90% confident, therefore correct” | “the model emitted 0.90 confidence; calibration/correctness were evaluated separately” |
| “the example validates GP3” | “the example demonstrates the software workflow on synthetic/demo data” |

Continue with the [Study lifecycle](study-lifecycle.md), [Publication-readiness checklist](publication-readiness.md), and [Validation guide](validation-evidence-guide.md).
