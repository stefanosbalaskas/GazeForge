# Structural validation-scope certificates

Validation claims in repeated-measures eye-tracking data depend on **what is actually separated between training and test partitions**. A random sample split can be statistically disjoint at the row level while still reusing the same trial or participant on both sides. GazeForge therefore derives validation scope from exact identities rather than trusting a user-supplied label such as “subject-independent”.

## Scope hierarchy

`derive_validation_scope()` assigns the strongest scope supported by the observed split:

| Scope | Structural requirement | Claim boundary |
| --- | --- | --- |
| `sample_level` | At least one exact participant/trial/sample identity occurs in both partitions. | No sample-disjoint claim. |
| `trial_level` | No exact sample overlap, but at least one participant/trial pair occurs in both partitions. | Sample-disjoint only. |
| `participant_within` | Trials are disjoint, but at least one participant occurs in both partitions. | Trial-disjoint; not subject-generalisation evidence. |
| `participant_disjoint` | No participant occurs in both partitions. | Structurally eligible for subject-generalisation claims, subject to all other scientific requirements. |
| `dataset_external` | Participants are disjoint and complete dataset identities are also disjoint. | Structurally eligible for cross-dataset generalisation claims, subject to all other scientific requirements. |

The hierarchy is deliberately conservative. Different dataset labels **do not** override participant overlap. Likewise, missing or incomplete dataset identities cannot produce `dataset_external`; the strongest possible result in that case is `participant_disjoint`.

## Required identities

Participant, trial, and sample identity columns are mandatory and must contain no missing or blank values. The default columns are:

```text
participant_id
trial_id
sample_index
```

Dataset identity defaults to `dataset_id`, but it is optional. Exact sample identity is the composite key `(participant_id, trial_id, sample_index)`, and duplicate composite sample keys inside either partition are rejected.

Using composite keys matters because trial or sample numbers are often reused across participants.

## Derive a scope

```python
from gazeforge.validation_scope import derive_validation_scope

assessment = derive_validation_scope(train, test)
print(assessment.scope)
print(assessment.counts)
```

The assessment stores overlap **counts** and deterministic SHA-256 fingerprints of the overlap identity sets. It does not embed raw participant, trial, or sample identifiers in the certificate payload.

## Require a minimum scope

A workflow that intends to make a subject-generalisation claim can fail closed before model evaluation:

```python
from gazeforge.validation_scope import (
    assert_validation_scope,
    derive_validation_scope,
)

assessment = derive_validation_scope(train, test)
assert_validation_scope(assessment, "participant_disjoint")
```

If a participant occurs in both partitions, the assertion raises rather than accepting a caller-declared “subject-independent” label.

For cross-dataset evaluation, require `dataset_external` instead.

## Replayable certificate

`build_validation_scope_certificate()` binds the structural assessment to the exact train and test tables:

```python
from gazeforge.validation_scope import build_validation_scope_certificate

certificate = build_validation_scope_certificate(
    train,
    test,
    minimum_scope="participant_disjoint",
)
```

The certificate contains:

- exact train and test table fingerprints;
- the identity-column mapping used for inference;
- the structurally derived scope and scope rank;
- train/test/overlap counts at sample, trial, participant, and dataset levels;
- fingerprints of the overlap identity sets;
- an optional minimum required scope; and
- a fixed claim boundary derived from the structural scope.

The claim boundary explicitly records that the certificate:

- establishes **structural split scope only**;
- does **not** verify that a column named `participant_id` truly represents biological participant identity;
- does **not** establish model performance;
- does **not** by itself establish external validity; and
- only marks subject- or cross-dataset-generalisation claims as structurally *eligible* when the relevant identities are disjoint.

## Exact-input replay

A certificate is not accepted merely because its JSON fingerprint is internally consistent. `validate_validation_scope_certificate()` rebuilds the complete certificate from the supplied train/test tables and requires exact equality:

```python
from gazeforge.validation_scope import validate_validation_scope_certificate

validate_validation_scope_certificate(certificate, train, test)
```

This prevents a modified certificate from promoting `participant_within` to `participant_disjoint`, even if someone recomputes the outer certificate fingerprint after editing the JSON.

Changing any value in either bound table also invalidates replay because the full table fingerprints are part of the certificate.

## Freeze only after replay

```python
from gazeforge.validation_scope import freeze_validation_scope_certificate

freeze_validation_scope_certificate(
    certificate,
    "validation/scope-certificate.json",
    train=train,
    test=test,
)
```

Freezing always performs exact-input replay first and refuses to overwrite an existing certificate by default.

## Scientific interpretation

A `participant_disjoint` certificate answers one narrow but important question: **are participant identities structurally separated across this specific train/test split?** It does not answer whether the participant IDs are correct, whether preprocessing leaked information, whether hyperparameters were tuned on the test data, whether the benchmark is representative, or whether performance is scientifically adequate.

A `dataset_external` certificate is similarly necessary but not sufficient for a cross-dataset generalisation claim. Dataset independence, provenance, annotation quality, device differences, preprocessing lineage, and model-selection leakage still require separate evidence.
