---
description: Reviewer-facing guide for reproducibility classes, rerun plans, claim-artifact traceability, software identity, limitations, and archive boundaries.
search:
  boost: 1.5
---

# Reviewer & replication handoff

<div class="gf-doc-kind" role="note" aria-label="Documentation type">
<strong>Reviewer handoff</strong> · Help an external reader inspect, rerun, and audit a frozen study without confusing reproducibility with scientific validity.
</div>

<nav class="gf-help" aria-label="Documentation help">
<a href="gazeforge-tour.md">Tour</a>
<a href="documentation-map.md">Task map</a>
<a href="troubleshooting.md">Troubleshooting</a>
<a href="runnable-examples.md">Examples</a>
<a href="https://github.com/stefanosbalaskas/GazeForge/issues">Ask / report</a>
</nav>

Use this page after the source contract, QC/review decisions, analysis derivatives,
statistical handoff, measurement interpretation, and manuscript-facing reporting are
already frozen. The goal is narrower than analysis: make the archive understandable
and rerunnable **to the extent the available data, privacy rules, and licences allow**.

!!! warning "Reproducibility is not validity"
    Matching hashes, deterministic reruns, and a complete archive can establish
    artifact/software identity and improve auditability. They do **not** establish
    tracker validity, native-rate validity, event-model validity, measurement or
    construct validity, causal validity, or external validity.

## Run the worked reviewer bundle

```bash
python examples/14_worked_reviewer_replication_bundle.py \
  --output-dir worked-reviewer-replication-bundle
```

The base-install demonstration writes:

```text
01_claim_artifact_matrix.csv
02_rerun_plan.csv
03_reproducibility_checklist.csv
04_limitations_register.csv
05_api_route_map.csv
software_environment.json
reviewer_start_here.md
artifact_hash_ledger.csv
replication_manifest.json
```

The example is `synthetic_demo_not_empirical_evidence`. It packages reviewer-facing
metadata only; it does not run a new scientific analysis or redistribute private data.

## Three reproducibility classes

| Class | Meaning | What the reviewer can do | Do not imply |
| --- | --- | --- | --- |
| `fully_rerunnable_demo` | deterministic worked software example with no restricted input | rerun the documented example and compare emitted artifacts/hashes | empirical validity or performance on real participants |
| `rerunnable_with_private_input` | analysis route is specified but real input requires authorized/private access | rerun once the authorized source is supplied in the declared environment | that the private source is bundled or publicly redistributable |
| `inspectable_only` | permitted frozen derivatives/manifests can be shared, but source-dependent calculations cannot be rerun from the archive alone | inspect provenance, methods, hashes, denominators, and permitted outputs | full computational reproducibility |

Do not collapse these classes into a single “reproducible” label.

## Reviewer reading order

A useful archive should answer the reviewer’s questions in this order:

1. **What is this bundle?** Open the bundle manifest and start-here file.
2. **Which files support which statements?** Open the claim–artifact matrix.
3. **What can I rerun?** Open the rerun plan and input-access status.
4. **What was the software identity?** Check release/version/full commit and environment metadata.
5. **Do denominators reconcile?** Trace source → pre-review QC → reviewed exclusions → primary derivative.
6. **What interpretation is supported?** Read the measurement/interpretation audit and limitations register.
7. **Which public API produced each layer?** Use the API route map.
8. **What cannot be shared or inferred?** Read privacy/licensing and evidence-boundary statements.

## Claim → artifact → API traceability

For every material manuscript statement, keep the route reconstructable:

| Statement type | Supporting artifact | Public route | Boundary |
| --- | --- | --- | --- |
| canonical/source schema identity | source contract + canonical table | [Schema API](api-reference.md#schema) | reconstructable schema ≠ correct source semantics |
| QC was reviewed rather than applied automatically | pre-review QC + review ledger | [Quality-control API](api-reference.md#quality-control) | reproducible rule ≠ validated rule |
| event outputs used a declared detector/model | event samples/intervals + method identity | [Eye-events API](api-reference.md#eye-events) | algorithm output ≠ physiological ground truth |
| fixations were assigned to declared AOIs | AOI definitions + fixation assignments | [Semantic AOI API](api-reference.md#semantic-aois) | AOI membership ≠ trust/interest/comprehension |
| moving AOIs were evaluated only within reviewed temporal support | keyframes/tracks + interpolation audit | [Dynamic AOI API](api-reference.md#dynamic-aois) | do not extrapolate outside reviewed support |
| scanpaths summarize observable sequence structure | semantic scanpaths/transition tables | [Scanpath API](api-reference.md#scanpaths) | sequence ≠ latent strategy/diagnosis |
| reviewer-facing plots/diagnostics are traceable to frozen derivatives | figure/diagnostic inventory | [Visual diagnostics API](api-reference.md#visual-diagnostics) | reproducible figure ≠ empirical validity |
| held-out structure matches the stated generalisation unit | split ledger/certificate | [Structural validation API](api-reference.md#structural-validation-scope) | structural split integrity ≠ empirical validity |
| rate sensitivity was evaluated under declared derivation rules | sampling-sensitivity outputs | [Sampling-sensitivity API](api-reference.md#sampling-sensitivity) | derived rate ≠ native-device validity |

A hash identifies bytes. It does not make the scientific interpretation correct.

The worked claim-artifact matrix also retains explicit `evidence_classification`, `artifact_access`, and `bundled_by_default` fields for every claim row. Private or study-specific artifacts are therefore represented as required inputs/identities rather than being implied to be bundled with the public teaching archive.

## Rerun plan by access scenario

### Public/synthetic input

Provide an exact command, version/commit identity, expected output inventory, and
hash/checksum rules. A rerun should produce the same deterministic artifacts where
the workflow contract promises determinism.

### Private participant data

Do **not** copy private/raw data into a public archive merely to make the rerun easier.
Instead provide:

- the authorized access route;
- expected schema/source contract;
- exact analysis command;
- software/environment identity;
- permitted derived artifacts and hashes;
- a statement of what cannot be independently rerun without access.

### Licensed/restricted external source

Technical ability to download or package a file does not override licensing. Record
source identity, version/revision, licence/reuse status, and the permitted acquisition
route. If redistribution is not authorized, mark the workflow
`rerunnable_with_private_input` or `inspectable_only` as appropriate.

## Software and environment identity

For a released analysis, record at least:

- GazeForge version;
- Python version;
- material optional dependencies;
- OS where material to the workflow;
- exact configuration/thresholds/seeds;
- acquisition/preprocessing/model identities;
- input/output fingerprints.

For a development checkout, also record the **full Git commit SHA**. “Latest main” is
not a reproducible software identity.

See [Release & install](release-install.md), [Reproducible reporting](reproducible-reporting.md),
and the [API reference](api-reference.md).

## Denominators, exclusions, missingness, and censoring

A reviewer should be able to reconstruct the denominator transition, not only inspect
the final analysis table. Preserve:

- source denominator;
- pre-review QC denominator;
- sample/trial/participant review decisions;
- primary-analysis denominator;
- exposure denominators for rate/proportion/dwell outcomes;
- missing versus observed zero versus absent-by-design states;
- event indicators and censor times for no-fixation latency.

Never use `fillna(0)` as a replication convenience when the original estimand
requires missingness or censoring. Use the [Analysis handoff](analysis-handoff.md) for
the model-ready contract and [Publication readiness](publication-readiness.md) for the
submission audit.

## Interpretation and limitations that must travel with the archive

At minimum, carry forward these limitations when relevant:

- synthetic/demo output is not empirical validation evidence;
- import compatibility is not device validity;
- observed timestamp cadence is not proof of native hardware rate;
- derived-rate evidence is not native-rate validation;
- QC flags are not automatic invalidity or exclusions;
- event/AOI/scanpath outputs do not automatically measure latent psychological constructs;
- structural split integrity is not empirical model validity;
- matching hashes establish file identity, not truth;
- reviewer inspectability is not equivalent to a complete independent rerun;
- privacy and licensing remain independent from technical packagability.

Use the [Measurement & interpretation clinic](measurement-interpretation.md) before
promoting a gaze-derived observable into a substantive construct.

## Reviewer questions and stop conditions

Stop and resolve the issue before describing a result as reproducible if:

- the exact software version/commit is unknown;
- the source contract or unit conversions were guessed;
- the stated rerun requires an unavailable input that is not disclosed;
- exclusion denominators cannot be reconciled;
- missing values were silently converted to zero;
- a latency without fixation was assigned an invented latency instead of censoring;
- a dynamic AOI is used outside reviewed temporal support;
- a held-out claim does not name the actual held-out identity;
- the archive claims a stronger evidence class than the underlying study supports.

## Copy-ready reporting patterns

### Reproducibility statement

> Analysis artifacts were frozen with explicit software identity, source/derivative provenance, rerun commands, and SHA-256 file identities. Reproducibility metadata were treated as audit evidence and were not interpreted as independent evidence of measurement, device, model, construct, causal, or external validity.

### Software identity

> Analyses used GazeForge `<version>` under Python `<version>` with `<material dependencies>`. Development-checkout analyses additionally record full Git commit `<sha>` and the frozen analysis configuration.

### Data-availability statement

> Source data are `<public/private/restricted>`. `<Permitted derivatives>` are archived with provenance and hashes. Reproducing source-dependent calculations requires `<authorized access route>`; restricted/private source files are not redistributed by the analysis archive.

### Limitations statement

> The archive supports inspection and `<fully rerunnable / authorized-input rerunnable / inspectable-only>` reproducibility for the declared workflow. Matching artifacts do not establish native-device validity, construct validity, model generalisation beyond the stated evaluation design, or a causal/psychological interpretation of gaze-derived measures.

### Reviewer archive statement

> Reviewers should begin with `replication_manifest.json` and `reviewer_start_here.md`, then use the claim–artifact matrix and rerun plan to trace each material statement to its supporting artifact, access requirement, API route, and interpretation boundary.

## What not to bundle by default

Do not copy these into a public archive without an explicit right/need to do so:

- identifiable participant exports;
- restricted benchmark/source files;
- credentials, tokens, or local paths containing secrets;
- proprietary stimuli without redistribution permission;
- intermediate files whose only purpose is convenience and whose provenance is unclear.

A reproducibility archive should improve transparency without creating a new privacy,
licensing, or governance problem.

## Continue through the publication path

- [Research evidence bundle](research-evidence-bundle.md) — freeze source/QC/review/analysis/provenance layers.
- [Analysis handoff](analysis-handoff.md) — preserve inferential units, denominators, missingness, and censoring.
- [Measurement & interpretation clinic](measurement-interpretation.md) — audit what gaze-derived measures can support.
- [Reporting & interpretation clinic](reporting-clinic.md) — write Methods/Results/captions without strengthening evidence.
- [Publication readiness](publication-readiness.md) — final preregistration/submission/archive audit.
- [API reference](api-reference.md) — exact public interfaces behind the workflow.

## Evidence boundary

The worked reviewer bundle is `synthetic_demo_not_empirical_evidence`. It performs no
new scientific analysis, bundles no private/restricted source, and creates no device,
native-rate, model, measurement/construct, causal, or latent-state validity claim.
