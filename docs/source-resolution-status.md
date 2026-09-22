# Source-resolution status

!!! warning "Governance status, not performance evidence"
    This page reports integrity-checked source-resolution checkpoints. A row may
    reference separately frozen empirical source evidence when that evidence has
    actually been created, but the dashboard itself does **not** establish model
    performance, human-human reliability, analysis rights, redistribution rights,
    source-audit readiness, or Frozen Evidence publication.

The table is generated from the committed `source-resolution-status-v1` JSON records and
their dataset-specific validators. Values are not transcribed by hand.

| Dataset | Checked | Resolution status | Analysis use | Raw redistribution | Audit ready | Empirical evidence | Record fingerprint |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Gaze-in-the-Wild naturalistic eye-head event benchmark | 2026-09-05 | `published_distribution_identifier_established_current_direct_copy_unverified` | unresolved | unresolved | false | false | `22bbdef6e6f2…` |
| Hollywood2EM eye-movement event benchmark | 2026-09-05 | `canonical_repository_and_ground_truth_recovered_terms_and_participant_mapping_unresolved` | unresolved | unresolved | false | true | `cd08d220357f…` |
| VISUS dynamic-video eye-tracking benchmark | 2026-09-04 | `current_authoritative_distribution_unresolved` | unresolved | unresolved | false | false | `6196ebdb9a5a…` |

## Bundle identity

The complete currently discovered checkpoint set has deterministic validation-bundle
fingerprint:

`57064fea405e4a2e944bb066dd2dd7bff919ec12fb380d9cc1a8ba67d3bbbc5a`

Changing any validated checkpoint changes this bundle identity. Duplicate datasets,
malformed governed files, unsupported datasets, or unsupported evidence-state
transitions fail before this page is generated.

## Reviewed governance snapshot

The live validation bundle exactly matches the separately frozen reviewed
source-resolution snapshot dated **2026-09-05**.

Reviewed lock fingerprint:

`705fab1f67b564da5deef8c004822c424e714037ec4e0067831fad8cbee3e713`

This lock confirms only that the public status page matches the checkpoint
contents intentionally reviewed for repository governance. It does **not**
authorize source-status upgrades, source-audit readiness, empirical evidence,
dataset analysis or redistribution rights, or Frozen Evidence publication.
A checkpoint may point to empirical evidence only when that evidence is
independently frozen and validated outside the governance lock.

## Scientific boundary

Source resolution and source evidence do not automatically imply source-audit
readiness or benchmark performance. The Frozen Evidence layer remains a separate
publication gate for validated performance results. A source-resolution row must
never be interpreted as benchmark accuracy, independent human reliability, GP3
validity, or permission to redistribute raw data unless those claims are separately
supported and frozen.
