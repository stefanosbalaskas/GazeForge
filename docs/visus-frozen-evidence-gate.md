# VISUS Frozen Evidence bundle gate

A completed VISUS validation suite is not, by itself, sufficient for publication in GazeForge's Frozen Evidence layer. The current gate is **v3** and requires the complete protocol-bound lineage introduced by the guarded VISUS workflow:

1. a pre-execution protocol frozen before detector inference;
2. the protocol-bound Grounding DINO + SAM 2 prediction batch;
3. the protocol-bound model-human validation binding;
4. the isolated source-authority transition seal;
5. the authority-bound validation-suite clone; and
6. strict five-input raw-execution provenance with the reviewed authority-certificate semantics revalidated.

A legacy suite plus execution-provenance pair is therefore no longer sufficient for scientific-review eligibility.

## Public Python entry points

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

## Strict command-line review path

```bash
gazeforge-visus evidence-validate /path/to/authority-transition
```

`evidence-validate` deliberately has no suite-only, execution-only, or legacy-v2 eligibility mode. It requires the v3 lineage to resolve completely. Lower-level validation commands remain useful for diagnostics, but they are not substitutes for the publication-review gate.

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

## Dashboard behavior

The public benchmark dashboard uses this same gate when it discovers a VISUS suite. A suite is not surfaced merely because its completion manifest and child reports are internally valid. The v3 transition seal, exact #130 binding, authority-bound suite, and strict execution provenance must all resolve and verify.

This means an older VISUS directory containing only a suite manifest and `visus-execution-provenance.json` now fails closed instead of appearing publication-ready. Lund and other non-VISUS suite paths are unchanged.

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

## Why v2 was insufficient

The previous v2 gate required an authority-bound suite plus strict execution provenance. That was a strong raw-input and authority-integrity check, but it did not require the newer #130 protocol-validation binding or #131 transition seal. A caller could therefore reach `frozen_evidence_eligible_for_scientific_review=true` without proving that model inference and validation were tied back to the pre-execution protocol.

v3 closes that bypass. The review-eligibility chain is now:

**pre-execution protocol → protocol-bound prediction batch → protocol-bound model-human validation → isolated authority transition → authority-bound suite → strict five-input execution provenance → Frozen Evidence review eligibility**.

Every arrow is an integrity/provenance statement. None of them, individually or together, substitutes for scientific interpretation of the empirical result.
