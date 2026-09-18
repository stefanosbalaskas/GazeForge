---
description: Build a reviewer- and replicator-facing handoff that maps claims to exact artifacts, hashes, rerun prerequisites, API routes, data-access constraints, and scientific limitations.
search:
  boost: 1.7
---

# Reviewer & replication handoff

<div class="gf-doc-kind" role="note" aria-label="Documentation type">
<strong>Reproducibility handoff</strong> · Help an external reviewer or replicator trace reported statements to exact artifacts, rerun routes, software identity, access prerequisites, and scientific boundaries.
</div>

<nav class="gf-help" aria-label="Documentation help">
<a href="gazeforge-tour.md">Tour</a>
<a href="documentation-map.md">Task map</a>
<a href="troubleshooting.md">Troubleshooting</a>
<a href="runnable-examples.md">Examples</a>
<a href="https://github.com/stefanosbalaskas/GazeForge/issues">Ask / report</a>
</nav>

Use this page after the analysis, evidence bundle, measurement-interpretation audit, and manuscript-facing reporting layer are frozen. Its question is not “is the study valid?” but **“can an external reader understand exactly what was done, what can be rerun, what requires access, and what each artifact does and does not establish?”**

!!! warning "Reproducibility is not validity"
    Deterministic reruns, matching hashes, complete archives, and reviewer inspectability support auditability. They do **not** establish device validity, native-rate validity, measurement validity, model validity, construct validity, causal validity, or external validity.

## Reviewer reading order

A compact archive should let a reviewer answer the important questions without opening source code first.

1. **Start-here record** — what to read, in what order, and what the archive claims.
2. **Claim → artifact matrix** — which exact artifact supports each reported statement.
3. **Rerun plan** — command/action, prerequisites, data access, and expected outputs.
4. **Hash ledger** — exact SHA-256 identity of bundled derivatives.
5. **Reproducibility checklist** — what is demonstrably rerunnable versus still required.
6. **Limitations register** — scientific, access, licence, and generalisation boundaries.
7. **API route map** — public GazeForge interface behind each artifact family.
8. **Software/environment record** — release/commit, Python, and dependency-lock expectations.

The worked example writes exactly that structure.

## Three reproducibility classes

Use one of these closed-set classes for each rerun route.

| Class | Meaning | Typical example |
| --- | --- | --- |
| **fully_rerunnable** | all required teaching/public inputs are available and the route can be rerun from the recorded environment | deterministic synthetic GazeForge examples |
| **rerunnable_with_private_input** | code and configuration are available, but lawful rerun requires authorised private/restricted source data | participant-level empirical tracker exports |
| **inspectable_only** | archived reports, hashes, and provenance can be audited, but source access/rights prevent a default rerun | restricted benchmark or non-redistributable source |

Do not describe an archive as “fully reproducible” when the actual class is weaker. A study can still be highly auditable when lawful source access is restricted, but the access boundary must be explicit.

## Claim → artifact → hash → API

Every manuscript-facing statement should be traceable to an artifact role rather than to a vague folder name.

| Statement type | Study artifact | Reviewer question | API route | Scientific boundary |
| --- | --- | --- | --- | --- |
| denominator after review | exclusion/denominator flow | do acquired, excluded, and retained units reconcile? | [Quality-control API](api-reference.md#quality-control) | reproducible exclusion accounting ≠ validated exclusion rule |
| primary analysis rows | reviewed analysis derivative | can these rows be reconstructed from frozen review decisions? | [Schema API](api-reference.md#schema) | reconstructability ≠ measurement or causal validity |
| AOI dwell/count outcome | trial × AOI table | which fixation/event/AOI definitions produced the value? | [Eye-events](api-reference.md#eye-events) · [Semantic AOIs](api-reference.md#semantic-aois) | AOI metrics ≠ trust/persuasion/interest |
| no-fixation latency | trial × AOI table + censoring fields | were no-event trials retained as censored rather than zero? | [Eye-events](api-reference.md#eye-events) | correct censoring record ≠ estimator validation |
| semantic sequence result | reviewed fixation/AOI assignments + scanpath table | can the sequence be reconstructed from the assignment policy? | [Scanpaths](api-reference.md#scanpaths) | sequence structure ≠ latent strategy/intent |
| validation claim | split ledger + predictions + metrics | what exact unit was held out and what sampling condition was evaluated? | [Structural validation](api-reference.md#structural-validation-scope) · [Sampling sensitivity](api-reference.md#sampling-sensitivity) | reproducible evaluation ≠ universal/general validity |

For every bundled file, retain a deterministic hash. For non-bundled private/restricted files, retain the study-side hash or authoritative source identifier when lawful and feasible; do not invent a placeholder hash and present it as verified.

### Public API routes a reviewer may need

- [Canonical schema / source handoff](api-reference.md#schema)
- [Quality-control evidence](api-reference.md#quality-control)
- [Eye-event construction](api-reference.md#eye-events)
- [Static semantic AOIs](api-reference.md#semantic-aois)
- [Dynamic semantic AOIs](api-reference.md#dynamic-aois)
- [Semantic scanpaths](api-reference.md#scanpaths)
- [Visual diagnostics](api-reference.md#visual-diagnostics)
- [Structural validation / generalisation scope](api-reference.md#structural-validation-scope)
- [Sampling sensitivity](api-reference.md#sampling-sensitivity)

The reviewer bundle records these as route IDs so a claim or rerun stage can point to the relevant documented interface without implying that API availability establishes scientific justification.

## Rerun planning

A useful rerun record has at least:

~~~text
stage: <what is being regenerated>
reproducibility_class: <fully_rerunnable | rerunnable_with_private_input | inspectable_only>
command_or_action: <exact command / archived script / inspection action>
software_identity: <release DOI or exact commit>
environment_identity: <Python + dependency lock>
input_identity: <source fingerprint / archive reference>
data_access_requirement: <none / authorised private input / independent acquisition>
expected_outputs: <artifact names>
scientific_boundary: <what successful rerun does not establish>
~~~

### Fully rerunnable teaching route

~~~bash
python examples/14_worked_reviewer_replication_bundle.py \
  --output-dir worked-reviewer-replication-bundle
~~~

### Empirical route with private input

A real empirical archive can record a study command such as:

~~~text
python <archived-study-script> --stage source-to-analysis
~~~

but should also state that the exact participant/source files must be supplied under the study's authorised data-access procedure.

A command alone does not make restricted data public.

## Software and environment identity

For the immutable public alpha, record the released artifact and version DOI:

~~~text
gazeforge==0.1.0a1
DOI: 10.5281/zenodo.22650013
~~~

For development analyses, record the **exact full Git commit** rather than “latest GazeForge”.

A reviewer-facing environment record should also name:

- Python version;
- dependency lock or frozen environment export;
- optional extras actually used;
- operating-system/platform information when it can affect the workflow;
- random seeds where the method is stochastic;
- model/configuration fingerprints where relevant.

The deterministic teaching example intentionally does **not** embed its live Python runtime into the output bytes, so the example stays byte-identical across supported runtimes. A real empirical archive should capture the actual runtime.

See [Citation & attribution](citation-attribution.md) and [Release & install](release-install.md).

## Denominators belong in the replication handoff

A reviewer should be able to reconcile:

- acquired participants;
- analysed participants;
- acquired trials;
- excluded trials and reasons;
- retained trials;
- source sample rows;
- pre-review QC rows;
- reviewed analysis rows;
- unavailable/absent-by-design AOI rows;
- no-fixation censored observations.

Do not provide only the final model N when the upstream denominator changed through review or missing exposure.

The [Analysis handoff](analysis-handoff.md) and [Artifact & output dictionary](artifact-dictionary.md) define these layers.

## Private data, licensing, and redistribution

Technical ability to copy a file is not permission to redistribute it.

Keep these questions separate:

- **Can the analysis code run?**
- **Can the reviewer legally/ethically receive the source data?**
- **Can the source be redistributed publicly?**
- **Can a reviewer independently acquire the original source?**
- **Can the archived derivative be shared when the source cannot?**

A private/restricted empirical source should normally be represented in the public reviewer bundle by identity/provenance metadata, hashes where lawful, data-availability instructions, and the exact rerun prerequisite—not by silently embedding the source.

Participant privacy, consent, institutional agreements, benchmark licences, and third-party rights remain independent constraints.

## Reviewer questions and stop conditions

### Stop: claim has no artifact

Every substantive reported statement should map to a concrete table, figure, model record, or archived decision record.

### Stop: hash is missing for a bundled derivative

If the file is bundled and intended to be immutable, give it a deterministic identity.

### Stop: source access is required but described as public

Classify the rerun honestly as `rerunnable_with_private_input` or `inspectable_only`.

### Stop: “reproducible” is being used as a validity claim

A script producing the same output twice does not validate the tracker, event method, AOI construct, model, psychological interpretation, causal contrast, or generalisation scope.

### Stop: software identity says “latest”

For a manuscript-facing development analysis, pin the exact commit and environment.

### Stop: native/derived sampling identity is missing

A reproducible derived 60 Hz pipeline is still derived 60 Hz. It does not become native-device evidence.

### Stop: reviewer cannot reconcile denominators

Return to the exclusion/denominator ledger before freezing the archive.

## Limitations register

The reviewer handoff should carry limitations as structured records rather than relying on one generic paragraph.

Minimum areas include:

- technical reproducibility versus scientific validity;
- private/restricted data access;
- source licensing and redistribution;
- native versus derived sampling;
- device/model/measurement validation scope;
- AOI/scanpath construct boundaries;
- population/stimulus/task generalisation;
- environment/software identity;
- unresolved source or annotation provenance;
- analyses that are exploratory rather than preregistered.

A limitation can be **inspectable and reproducible** without being resolved.

## Copy-ready archive statements

### Reproducibility statement

> The archived workflow records the exact software identity, analysis configuration, artifact inventory, and deterministic fingerprints used for the reported analysis. Rerun availability is classified separately for public teaching artifacts, private-input stages, and inspectable-only evidence. Reproducibility is not interpreted as evidence of device, measurement, model, construct, causal, or external validity.

### Software statement

> GazeForge was identified by its exact archived release or full development commit. The corresponding Python/dependency environment was retained with the study materials.

### Data-availability statement

> Analysis code and reviewer-facing derivatives are archived. Participant/source files are not redistributed by default; authorised access to restricted inputs follows the study's stated data-access procedure. File identity/provenance is retained separately from redistribution permission.

### Limitations statement

> The archive supports reconstruction and audit of the declared workflow. It does not by itself establish the validity of the tracker, event detector, AOI construct, downstream statistical model, substantive psychological interpretation, causal contrast, or generalisation beyond the studied population/tasks.

### Archive statement

> Reported statements are mapped to exact artifact names and, for bundled derivatives, SHA-256 identities. Non-bundled private/restricted source artifacts are represented through the strongest lawful identity/provenance record available.

## Worked reviewer/replication bundle

Run:

~~~bash
python examples/14_worked_reviewer_replication_bundle.py \
  --output-dir worked-reviewer-replication-bundle
~~~

The example writes:

~~~text
01_claim_artifact_matrix.csv
02_rerun_plan.csv
03_reproducibility_checklist.csv
04_limitations_register.csv
05_api_route_map.csv
artifact_hash_ledger.csv
software_environment.json
reviewer_start_here.md
replication_manifest.json
~~~

The bundle is deterministic and `synthetic_demo_not_empirical_evidence`.

It verifies that:

- reproducibility classes are drawn only from the declared closed set;
- claim rows retain an evidence class and interpretation boundary;
- private/restricted study artifacts are not bundled by default;
- emitted reviewer derivatives have matching SHA-256 hashes;
- no source, QC, review, event, AOI, or analysis artifact is mutated;
- missing values are not converted to zero;
- no device/native-rate/measurement/model/construct/causal/external-validity or psychological-state claim is created;
- reproducibility is not equated with validity.

## Continue through the publication/archive path

- [Outcome & estimand preregistration](estimand-preregistration.md) — planned outcomes and deviations.
- [Research evidence bundle](research-evidence-bundle.md) — source/QC/review/analysis/provenance freeze.
- [Analysis handoff](analysis-handoff.md) — model-ready tables and denominator/censoring semantics.
- [Measurement & interpretation clinic](measurement-interpretation.md) — observable→construct boundaries.
- [Reporting & interpretation clinic](reporting-clinic.md) — claim-safe manuscript wording.
- [Publication readiness](publication-readiness.md) — final pre-submission audit.
- [Reproducible reporting](reproducible-reporting.md) — manuscript-facing identity and evidence guidance.
- [API reference](api-reference.md) — exact documented public interfaces.
