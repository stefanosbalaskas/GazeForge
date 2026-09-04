# VISUS Frozen Evidence CLI validation

Use the final publication-integrity command only after a VISUS suite and its raw-execution provenance have both been frozen:

```bash
gazeforge-visus evidence-validate /path/to/frozen-visus-suite
```

The command calls the complete Frozen Evidence bundle gate. It revalidates the suite and all required child reports, revalidates the raw-execution provenance and sibling-suite binding, requires exactly four raw execution inputs, and cross-checks the source/suite identities before returning `status="verified-bundle"`.

Unlike the lower-level diagnostic commands, `evidence-validate` intentionally exposes no `--manifest-only` or `--provenance-only` option. A partial check cannot be used as the final publication-integrity decision.

A successful result means the bundle is structurally eligible for scientific review. It does not establish that the local VISUS copy is authoritative, that reuse or redistribution rights are correct, that two independent human annotation streams exist, that a human reference is ground truth, or that detector/tracker performance is scientifically adequate.
