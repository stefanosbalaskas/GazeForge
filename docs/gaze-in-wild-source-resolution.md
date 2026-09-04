# Gaze-in-the-Wild source-resolution status

GazeForge treats **published availability**, **current direct retrievability**, **exact-file identity**, and
**reuse permission** as separate scientific-provenance questions. This page records the current
public-source resolution status of the Gaze-in-the-Wild benchmark without turning publication
metadata into a completed source audit.

The machine-readable checkpoint is:

```text
validation/protocols/gaze-in-wild-source-resolution-2026-09-04.json
```

It is a **source-resolution status record, not empirical evidence**.

## What the publication establishes

The authoritative dataset publication is:

> Rakshit Kothari, Zhizhuo Yang, Christopher Kanan, Reynold Bailey, Jeff B. Pelz, and Gabriel J. Diaz.
> *Gaze-in-wild: A dataset for studying eye and head coordination in everyday activities*.
> Scientific Reports 10, 2539 (2020). DOI: `10.1038/s41598-020-59251-5`.

The paper reports data from 19 participants performing up to four naturalistic tasks: indoor
navigation, ball catching, object search, and tea making. The acquisition system included 120 Hz
binocular Pupil Labs eye-tracking glasses, an MPU-6050 IMU, and a ZED stereo RGB-D camera. A
substantial portion of the data was hand labelled by five trained annotators.

The paper explicitly states that the annotators made decisions independently. That is legitimate
published evidence about the annotation procedure. It is still distinct from verifying, in the
exact current distributed files, which independent streams are separately recoverable and whether
they share exactly the same underlying gaze samples.

The paper's data-availability statement identifies:

```text
http://www.cis.rit.edu/~rsk3900/gaze-in-wild/
```

as the location of compressed data and code.

## Current resolution result

A public-source pass on 2026-09-04 found several converging signals about the distribution identity:

- the 2020 Scientific Reports article names the RIT URL above;
- later event-detection evaluation material continues to direct users to the same RIT distribution;
- a recent practical guide to mobile eye tracking still lists the same dataset URL as an open-access
  resource; and
- the current RIT Perception for Movement Lab page lists **The Gaze-In-Wild Dataset** under
  Software/Data.

However, the current institutional lab page surfaces the publication record rather than a direct
data archive, and a current exact copy was not successfully retrieved from the historical RIT data
URL in this resolution environment. GazeForge therefore records:

```text
published_distribution_identifier_established_current_direct_copy_unverified
```

with:

- `published_distribution_identifier_found=true`;
- `current_institutional_dataset_listing_found=true`;
- `current_direct_data_endpoint_verified=false`;
- `source_audit_ready=false`;
- `empirical_evidence_created=false`.

A failed retrieval in this environment is **not** evidence that the benchmark has disappeared. It
means the exact current copy has not yet passed GazeForge's source-identity gate.

## Article licensing is not silently promoted to dataset licensing

The Scientific Reports article is published under CC BY 4.0. GazeForge does **not** infer from the
article license that all externally hosted raw gaze, imagery, annotation, or other dataset files are
covered by the same terms.

Similarly, the publication's statement that compressed data and code are publicly available does
not by itself establish unrestricted raw-data redistribution permission. Until the exact obtained
copy and its repository-level terms are reviewed, GazeForge keeps:

- analysis-use terms unresolved; and
- raw-data redistribution terms unresolved.

These permissions remain separate in the empirical source-audit specification.

## The 120 Hz / 300 Hz distinction is kept explicit

The primary paper unambiguously describes **120 Hz binocular Pupil Labs eye-tracking hardware**.
That value is acquisition-hardware provenance.

A later event-detection evaluation catalog describes Gaze-in-the-Wild as 300 Hz. GazeForge does not
silently choose one number, reinterpret one as the other, or force either nominal value onto the
files. The existing source-audit design instead infers the observed cadence of every reviewed
`LabelData` stream from its timestamps and records that separately from published hardware
provenance.

Accordingly:

- published acquisition hardware remains 120 Hz;
- the secondary 300 Hz catalog value remains a separately identified secondary description;
- the discrepancy remains unresolved at source-resolution stage; and
- empirical file cadence must come from exact audited timestamps.

This distinction prevents processed/distributed-file cadence from being misrepresented as tracker
hardware acquisition rate.

## Independent annotation is published, but file-level recoverability still needs verification

The paper reports five trained annotators and states that each labeller made decisions independently.
This is stronger provenance than a sequential correction workflow and supports treating the dataset
as a candidate for human-human agreement analysis.

Frozen agreement nevertheless remains blocked until an exact authoritative copy verifies:

1. the independently labelled streams are separately recoverable;
2. participant/task/labeller identities are unambiguous;
3. overlapping streams refer to the same `ProcessData` source;
4. timestamps and underlying gaze samples are identical before labels are compared; and
5. every file is bound to the audited source manifest.

Human disagreement, once measured on those verified streams, is a reference-variability result — not
an error-free ground-truth ceiling.

## What must happen next

The next empirical actions are:

1. obtain an exact current copy from the published RIT distribution or an author-verified
   institutional source;
2. verify analysis-use and raw-data redistribution terms separately from that exact copy;
3. inventory and SHA-256 fingerprint all `LabelData` and `ProcessData` files;
4. verify participant/task identities and label-to-process pairing;
5. verify point-of-regard coordinate semantics;
6. infer each audited label stream's actual analysis cadence from timestamps;
7. verify independently recoverable overlapping labeller streams and freeze human-human agreement;
8. run participant-disjoint model validation with naturalistic-task and event-class sensitivity.

Until those gates pass, the Gaze-in-the-Wild software remains **validated audit/analysis
infrastructure with empirical execution pending**.

Gaze-in-the-Wild is complementary naturalistic head-mounted evidence. It is not Gazepoint GP3
validation and must not be used as a substitute for a native 60 Hz/GP3-class expert-labelled corpus.

## Public sources used for this checkpoint

- Scientific Reports dataset publication: <https://doi.org/10.1038/s41598-020-59251-5>
- Open full-text publication copy: <https://pmc.ncbi.nlm.nih.gov/articles/PMC7018838/>
- Current RIT Perception for Movement Lab: <https://www.rit.edu/science/perception-movement-lab>
- Event-detection evaluation replication repository:
  <https://github.com/r-zemblys/EM-event-detection-evaluation>
- Practical guide listing open-access mobile eye-tracking data:
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC11525247/>
- Published RIT distribution identifier:
  <http://www.cis.rit.edu/~rsk3900/gaze-in-wild/>

These sources document the resolution decision. They do not replace an exact-file source audit.
