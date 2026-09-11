# VISUS protocol → authority transition

GazeForge now has a fail-closed transition between the **protocol-bound VISUS validation handoff** and the existing **source-authority / authority-execution provenance** machinery.

This layer exists because the two mechanisms deliberately freeze different identities:

- the protocol-bound validation artifact freezes the **pre-authority validation-suite fingerprint**;
- the established authority binder adds the reviewed source-authority certificate identity to the suite manifest, which correctly creates a **new suite fingerprint**.

Applying the authority binder directly to the only copy of a protocol-bound suite would therefore destroy the exact suite identity recorded by the earlier validation binding. The transition layer avoids that mutation.

## Preservation rule

`run_visus_protocol_authority_transition()` first revalidates the complete protocol-bound validation run. It then refuses to continue unless:

- the original suite is still unmodified and not already authority-bound;
- the underlying VISUS source audit already carries a separately reviewed source-authority certificate; and
- the authority-transition output directory is separate from, and not nested inside, the original protocol-validation directory.

The original directory is never rewritten.

## Isolated suite clone

The transition copies only the completed validation-suite child reports and suite manifest into a new directory. Every copied child report must be byte-identical to the original.

The existing `bind_visus_suite_to_source_authority()` function is then applied to the **clone**, not the original.

The authority-bound clone must contain the exact source-authority certificate fingerprint in both:

```text
suite.source.source_authority_certificate_fingerprint_sha256
suite.protocol.source_authority_certificate_fingerprint_sha256
```

and must declare:

```text
suite.protocol.source_authority_certificate_bound = true
```

No model-human or human-human report is recomputed by this step.

## Pre → post authority proof

The core transition invariant is mechanical:

1. validate the post-authority suite and all child reports;
2. remove only the three authority additions from the post-authority suite manifest:
   - the source certificate fingerprint;
   - `source_authority_certificate_bound`;
   - the protocol certificate fingerprint;
3. recompute the suite fingerprint of that projection; and
4. require it to equal the exact suite fingerprint frozen by the original protocol-bound validation artifact.

Any other post-hoc suite-manifest change causes the transition to fail, even if the modified manifest is re-signed with a new valid suite fingerprint.

This proves that the authority-bound suite is the same completed scientific suite plus the reviewed authority identity, rather than a separately edited result.

## Exact byte lineage

The transition artifact also records SHA-256 identities for:

- the original protocol-validation binding file;
- the original pre-authority suite manifest;
- the post-authority suite manifest; and
- every child report file.

The validator rereads these files. Consequently, even whitespace-only byte drift in the original protocol-validation binding or original suite manifest is detectable at this layer, while any byte drift in copied child reports is rejected.

## Transition artifact

A successful transition writes:

```text
visus-protocol-authority-transition.json
```

The artifact binds:

- the exact source-audit identity;
- the reviewed source-authority certificate fingerprint;
- the frozen pre-execution protocol fingerprint;
- the complete protocol-bound model-batch fingerprint;
- the protocol-validation binding fingerprint and exact file SHA-256;
- the pre-authority suite fingerprint and manifest SHA-256;
- the post-authority suite fingerprint and manifest SHA-256; and
- an exact-byte ledger for every unchanged child report.

The transition itself is fingerprinted and revalidated.

## Existing authority execution remains authoritative

This layer does **not** replace `visus_authority_execution` or `visus_authority_execution_strict`.

After the isolated clone is authority-bound, the existing strict authority-execution path can consume that clone together with its five governed execution inputs:

1. source-audit specification;
2. source-authority certificate;
3. human AOI table;
4. model prediction table; and
5. timestamp-grid JSON.

That existing provenance layer remains responsible for binding the exact raw execution files and the exact certificate file bytes to the authority-bound suite.

The transition therefore closes the lineage gap:

```text
frozen pre-execution protocol
        ↓
complete protocol-bound model batch
        ↓
protocol-bound model-human validation
        ↓
[original validation preserved unchanged]
        ↓
isolated authority-bound suite clone
        ↓
strict five-input authority execution provenance
```

## Usage

```python
from gazeforge.visus_protocol_authority_transition import (
    run_visus_protocol_authority_transition,
)

transition = run_visus_protocol_authority_transition(
    validation,
    "outputs/visus-authority-transition",
)

print(transition.transition_fingerprint_sha256)
print(transition.authority_suite.suite_fingerprint_sha256)
```

`validation` must be a fully valid `VisusProtocolBoundValidationRun` whose underlying source audit is already authority-bound through the established reviewed-certificate mechanism.

## Scientific boundary

A successful transition establishes a provenance relationship. It does **not** by itself establish or promote:

- empirical Grounding DINO + SAM 2 performance;
- scientific adequacy of model-human metrics;
- independent human annotation streams;
- formal preregistration;
- Frozen Evidence;
- permission to redistribute raw VISUS source material; or
- authority to publish an empirical performance claim.

The artifact therefore keeps:

```text
empirical_validation_authorized_by_transition = false
empirical_performance_claim_created = false
formal_preregistration_verified = false
frozen_evidence_created = false
raw_source_redistribution_action_authorized = false
```

Source authority is **consumed from** the existing reviewed certificate; it is not invented or self-certified by this transition. Likewise, the existing authority-execution provenance remains a separate required downstream artifact.

Until a real current authoritative VISUS source and rights record is reviewed, certified, and used in a governed execution, this infrastructure must not be interpreted as empirical VISUS evidence.
