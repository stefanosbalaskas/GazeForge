# VISUS Frozen Evidence bundle gate

A completed VISUS validation suite is not, by itself, sufficient for publication in GazeForge's Frozen Evidence layer. The lineage-integrity gate is **v3** and requires the complete protocol-bound lineage introduced by the guarded VISUS workflow:

1. a pre-execution protocol frozen before detector inference;
2. the protocol-bound Grounding DINO + SAM 2 prediction batch;
3. the protocol-bound model-human validation binding;
4. the isolated source-authority transition seal;
5. the authority-bound validation-suite clone; and
6. strict five-input raw-execution provenance with the reviewed authority-certificate semantics revalidated.

A legacy suite plus execution-provenance pair is therefore no longer sufficient for scientific-review eligibility. Passing v3 is also **not** sufficient for public Frozen Evidence publication: the dashboard additionally requires a separate explicit scientific-review approval bound to the exact v3 lineage.

## Public Python entry points

The v3 eligibility gate remains:

```python
from gazeforge import (
    VisusFrozenEvidenceBundle,
    load_visus_frozen_evidence_bundle,
    validate_visus_frozen_evidence_bundle,
)

summary = validate_visus_frozen_evidence_bundle(
    "path/to/authority-transition"
)
bundle = load_visus_frozen_evidence_bundle(
    "path/to/authority-transition"
)
```

The authority-transition directory must contain:

- `visus-dynamic-aoi-suite-manifest.json`;
- every child report referenced by that suite;
- `visus-protocol-authority-transition.json`; and
- `visus-execution-provenance.json` produced by the strict authority-execution path.

The exact #130 `visus-protocol-bound-validation.json` remains in the original protocol-validation directory. The v3 gate reads the binding filename and exact file SHA-256 frozen by the #131 transition and searches the authority-transition directory's parent tree for one unique byte-identical binding. If the layout contains multiple identical copies, Python callers can remove the ambiguity explicitly:

```python
summary = validate_visus_frozen_evidence_bundle(
    "path/to/authority-transition",
    protocol_validation_binding_path=(
        "path/to/validation/visus-protocol-bound-validation.json"
    ),
)
```

This lookup does not modify or relocate the #130 validation directory.

## Strict command-line eligibility path

```bash
gazeforge-visus evidence-validate /path/to/authority-transition
```

`evidence-validate` deliberately has no suite-only, execution-only, or legacy-v2 eligibility mode. It requires the v3 lineage to resolve completely. Lower-level validation commands remain useful for diagnostics, but they are not substitutes for the review-eligibility gate. A successful `evidence-validate` result does not itself authorize dashboard publication.

## What v3 verifies

The gate first validates the authority-bound suite and every referenced child report. It then validates the #131 transition seal and requires:

- the transition schema, status, and deterministic fingerprint to revalidate;
- all transition claim-boundary flags to remain fail-closed;
- the post-authority suite fingerprint, report count, and exact manifest bytes to match the current suite;
- the transition's pre-authority projection fingerprint to equal the frozen pre-authority suite fingerprint;
- source-audit/spec/manifest and authority-certificate identities to match the authority-bound suite;
- every child report in the transition ledger to have the same filename, report fingerprint, and exact byte SHA-256 as the current authority suite.

The gate then resolves and validates the #130 protocol-validation binding. It requires:

- schema `gazeforge-visus-protocol-bound-validation-v1` and status `verified-protocol-bound-validation`;
- the binding fingerprint to recompute;
- the binding's exact file SHA-256 and semantic fingerprint to match the #131 transition;
- the pre-execution protocol fingerprint and protocol-batch fingerprint to match the transition;
- the binding's validation-suite fingerprint to identify the transition's exact pre-authority suite;
- source-audit/spec/manifest identities to remain unchanged across the authority transition;
- `prediction_emission_grid_used=false` in the frozen evaluation settings;
- model-human validation to have executed;
- source authority to remain a separate gate at the #130 layer; and
- all #130 claim-promotion fields to remain false.

Finally, strict authority-execution provenance is revalidated and must bind exactly five raw inputs, including the reviewed authority-certificate bytes. The execution suite fingerprint and authority-certificate fingerprint must equal the authority-bound suite identities, and certificate semantics must revalidate under the current closed schema.

A successful result reports:

```text
bundle = "visus-frozen-evidence-v3"
status = "verified-protocol-authority-bound-bundle"
protocol_bound_lineage_verified = true
frozen_evidence_eligible_for_scientific_review = true
scientific_review_completed = false
empirical_performance_claim_created = false
formal_preregistration_verified = false
```

The typed `VisusFrozenEvidenceBundle` also carries the transition fingerprint, protocol-validation binding fingerprint, pre-execution protocol fingerprint, protocol-batch fingerprint, suite fingerprint, execution fingerprint, and source-authority certificate fingerprint.

## Separate scientific-review approval

Public VISUS Frozen Evidence requires an additional file in the authority-transition directory:

```text
visus-scientific-review.json
```

The review artifact is a separate closed-schema decision record. It is **not generated from model metrics**. A reviewer must explicitly supply reviewer identity, an ISO-8601 UTC review timestamp, and a non-empty review rationale after scientific review has occurred.

The Python review path is intentionally separate from v3 eligibility:

```python
from gazeforge.visus_scientific_review import (
    build_visus_scientific_review_approval,
    validate_visus_scientific_review_approval,
    write_visus_scientific_review_approval,
)

record = build_visus_scientific_review_approval(
    "path/to/authority-transition",
    reviewer="Reviewer identity",
    reviewed_at="2026-09-11T18:30:00Z",
    review_rationale="Documented scientific review rationale.",
)

write_visus_scientific_review_approval(
    "path/to/authority-transition",
    reviewer="Reviewer identity",
    reviewed_at="2026-09-11T18:30:00Z",
    review_rationale="Documented scientific review rationale.",
)

validated = validate_visus_scientific_review_approval(
    "path/to/authority-transition"
)
```

The approval record binds the exact:

- authority-bound suite fingerprint;
- pre-authority suite fingerprint;
- strict execution fingerprint;
- protocol-authority transition fingerprint;
- protocol-validation binding fingerprint;
- pre-execution protocol fingerprint;
- protocol-bound prediction-batch fingerprint;
- source-authority certificate fingerprint;
- report count; and
- required five-input execution cardinality.

The record may promote only these publication-state fields:

```text
scientific_review_completed = true
approved_for_public_frozen_evidence = true
```

It must keep all of the following false:

```text
empirical_performance_claim_created
formal_preregistration_verified
independent_human_streams_verified
human_reference_ground_truth_promoted
source_authority_or_rights_expanded
raw_source_redistribution_authorized
evaluation_grid_boundary_changed
universal_performance_validity_claim_created
```

Changing any lineage identity invalidates the approval even if the review record is re-fingerprinted. Likewise, changing a prohibited claim to `true` remains invalid after re-fingerprinting. Existing review files are protected from replacement by default.

## Dashboard behavior

The public benchmark dashboard now enforces **two distinct VISUS gates**:

1. v3 lineage eligibility must validate completely; and
2. `visus-scientific-review.json` must validate as an explicit approval for the exact same suite.

A suite is therefore not surfaced merely because its completion manifest, child reports, transition seal, protocol-validation binding, authority certificate, and raw-execution provenance are internally valid. Those artifacts establish review eligibility. Publication requires the separate scientific-review decision.

An older VISUS directory containing only a suite manifest and `visus-execution-provenance.json` fails closed. A complete v3 directory without a scientific-review approval also fails closed instead of appearing under **Frozen benchmark evidence**. Lund and other non-VISUS suite paths are unchanged.

## What eligibility means

Eligibility is intentionally narrower than empirical validity. It means that the artifact chain is complete and internally consistent enough to be **considered for scientific review**. It does **not** mean that GazeForge has independently established that:

- a local VISUS copy is a current authoritative distribution;
- analysis or redistribution rights exist beyond the separately reviewed source-authority evidence;
- a human reference stream is ground truth;
- the historical two-contributor curation process represents two independent annotation streams;
- Grounding DINO + SAM 2 performance is scientifically adequate;
- model-emission frames can serve as the evaluation timestamp grid; or
- the pre-execution protocol constitutes formal preregistration.

Formal preregistration would require separate trusted temporal evidence. Independent human-stream evidence, empirical performance interpretation, source-authority/rights review, and final scientific review remain separate gates.

Even an approved public Frozen Evidence record is scoped only to GazeForge's reviewed evidence index. It does not create a universal performance-validity claim, convert the human reference into ground truth, expand source rights, authorize redistribution, or establish formal preregistration.

## Why v2 and v3 eligibility alone are insufficient

The previous v2 gate required an authority-bound suite plus strict execution provenance. That was a strong raw-input and authority-integrity check, but it did not require the newer #130 protocol-validation binding or #131 transition seal. A caller could therefore reach review eligibility without proving that model inference and validation were tied back to the pre-execution protocol.

v3 closes that lineage bypass. #133 closes the subsequent publication-layer bypass. The complete public path is now:

**pre-execution protocol → protocol-bound prediction batch → protocol-bound model-human validation → isolated authority transition → authority-bound suite → strict five-input execution provenance → v3 scientific-review eligibility → explicit scientific-review approval → public Frozen Evidence dashboard**.

Every arrow before the final approval is an integrity/provenance statement. The final approval is an explicit scoped review decision, not an automatically inferred scientific claim.
