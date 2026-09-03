# Gaze-in-the-Wild labeller agreement

GazeForge can quantify human-human event agreement for **Gaze-in-the-Wild only after the local
source copy has passed the source-audit contract**. The agreement runner consumes a verified
`GazeInWildSourceAuditRun`; it does not accept arbitrary label files or a caller-supplied claim that
two streams describe the same data.

## Why the runner is source-audit aware

The distributed corpus can contain multiple human label streams for one recording, and the cadence
actually present in `LabelData.T` should not be replaced by the nominal acquisition-hardware rate.
The runner therefore:

- revalidates the source-audit report and specification fingerprints;
- requires two distinct audited labeller IDs;
- checks the shared participant/trial inventory and requires complete overlap by default;
- re-aligns every shared trial one-to-one by participant, trial, and timestamp;
- rechecks point-of-regard, validity, and confidence identity between the paired streams;
- verifies that paired streams imply the same timestamp-derived sampling rate;
- computes sample-level exact agreement and Cohen's kappa;
- preserves excluded or invalid samples as temporal separators before event exclusion;
- segments each trial at **its own inferred source-file cadence**; and
- pools the resulting event intervals in milliseconds for bidirectional event matching.

This design avoids inventing one common sampling rate when an audited snapshot contains files with
different timestamp-derived cadences.

## Python workflow

```python
from gazeforge import (
    audit_gaze_in_wild_source,
    load_gaze_in_wild_source_audit_spec,
    run_gaze_in_wild_labeller_agreement,
)

spec = load_gaze_in_wild_source_audit_spec("gaze-in-wild-source-audit.json")
audit = audit_gaze_in_wild_source(
    "/path/to/LabelData",
    "/path/to/ProcessData",
    spec,
)

agreement = run_gaze_in_wild_labeller_agreement(
    audit,
    left_labeller=1,
    right_labeller=2,
    excluded_labels=("unlabelled",),
    exclude_invalid_tracking=True,
    event_min_iou=0.50,
)

print(agreement.report["metrics"]["sample_agreement_analysis_labels"])
print(agreement.report["metrics"]["event_agreement_left_as_reference"])
print(agreement.per_trial)
```

## Sample-level evidence

Two sample-level summaries are retained. The all-label summary describes the distributed annotation
streams as they exist. The analysis-label summary excludes configured non-analysis labels pairwise
and, by default, samples whose audited tracking-validity mask is false. The report records the
number and fraction of samples excluded from that analysis summary rather than deleting them
silently.

## Event-level evidence

Invalid or excluded samples are not removed before event segmentation. They remain hard temporal
separators so two same-labelled events on opposite sides of a tracking-loss or unlabelled run cannot
be accidentally joined into one event.

Event precision, recall, F1, temporal IoU, and onset/offset/duration errors are reported in both
labeller-reference directions. The left/right designations are bookkeeping only: neither human
labeller is treated as error-free.

## Overlap policy

`require_complete_overlap=True` is the default for frozen agreement evidence. If one selected
labeller is missing a participant/trial that exists for the other, the runner refuses to create the
report. Setting the option to `False` is available for controlled exploratory work; the report then
records left-only and right-only trial identities explicitly.

## Claim limit

This module completes the **agreement-analysis infrastructure**, not an empirical
Gaze-in-the-Wild result. A real agreement report should only be frozen after the authoritative
snapshot, current reuse terms, participant/task mapping, and coordinate semantics have been
independently audited.

Gaze-in-the-Wild is head-mounted naturalistic evidence from different hardware and conditions. Even
a fully audited human-human result must not be described as Gazepoint GP3-specific or native GP3
60 Hz validation.
