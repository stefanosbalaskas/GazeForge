# Study lifecycle

Use this page when you want to move from a research question to a manuscript-facing, auditable GazeForge analysis without treating the package as a collection of disconnected functions.

!!! warning "A complete workflow is not the same thing as validated evidence"
    Completing every stage below does **not** automatically validate a tracker, event model, AOI method, population, task, or sampling regime. The lifecycle keeps assumptions and evidence boundaries visible; empirical claims still depend on the relevant validation design. Use the [Validation guide](validation-evidence-guide.md) and generated [Evidence status](evidence-status.md) for current evidence claims.

<div class="gf-task-grid" markdown>

<div class="gf-task-card" markdown>

<span class="gf-task-kicker">1 · Plan</span>

### :material-file-document-edit-outline: Define the observable question

Specify what the gaze data can directly represent, the unit of analysis, acquisition requirements, AOI source, QC rule, and validation plan before fitting models.

[Researcher guidance →](for-researchers.md)

</div>

<div class="gf-task-card" markdown>

<span class="gf-task-kicker">2 · Prepare</span>

### :material-database-arrow-right-outline: Preserve and canonicalise

Keep the source immutable, fingerprint the analysed table, document time/coordinate semantics, and create a vendor-neutral canonical derivative.

[Import real data →](data-import-clinic.md)

</div>

<div class="gf-task-card" markdown>

<span class="gf-task-kicker">3 · Analyse</span>

### :material-chart-timeline-variant: QC, events, AOIs, sequences

Add non-destructive QC, start from inspectable event rules, preserve AOI provenance, and retain reviewable semantic sequence outputs.

[Run a complete workflow →](practical-workflow.md)

</div>

<div class="gf-task-card" markdown>

<span class="gf-task-kicker">4 · Validate</span>

### :material-shield-check-outline: Match evidence to the claim

Name the held-out unit, reference labels, acquisition provenance, rate status, calibration, and event-level metrics that actually support the intended claim.

[Inspect evidence →](validation-evidence-guide.md)

</div>

<div class="gf-task-card" markdown>

<span class="gf-task-kicker">5 · Freeze</span>

### :material-snowflake: Freeze identity and provenance

Archive the exact software/environment identity, source and output fingerprints, manifests, certificates, figures, tables, and unresolved evidence boundaries.

[Publication readiness →](publication-readiness.md)

</div>

<div class="gf-task-card" markdown>

<span class="gf-task-kicker">6 · Report</span>

### :material-text-box-check-outline: Write what was actually done

Translate acquisition, preprocessing, QC, model, split, rate, metric, and evidence identity into manuscript methods language that another team can reconstruct.

[Reproducible reporting →](reproducible-reporting.md)

</div>

</div>

## The ten-stage research route

| Stage | Input | Action | Reviewable output | Continue with | Do not infer |
| --- | --- | --- | --- | --- | --- |
| **1. Define the question** | substantive theory + task | define observable gaze construct and unit of analysis | analysis/preregistration plan | [For researchers](for-researchers.md) | latent states from gaze alone |
| **2. Record acquisition facts** | tracker/stimulus setup | record hardware, native rate, geometry, participant/trial identity | acquisition/source record | [Import clinic](data-import-clinic.md) | undocumented acquisition facts |
| **3. Preserve source identity** | original export/table | retain immutable source and fingerprint analysed source table | source snapshot + checksum/fingerprint | [Import clinic](data-import-clinic.md) | fingerprint = independent validation |
| **4. Canonicalise explicitly** | source semantics | map time, coordinates, identity, optional fields | canonical gaze table | [Adapters & validation](adapters-validation.md) | successful import = device validity |
| **5. Add QC evidence** | canonical samples | flag anomalies and score trial quality without silent deletion | QC columns + trial summaries | [Practical workflow](practical-workflow.md) | QC flag = invalid observation |
| **6. Build measurement outputs** | reviewed samples | apply event baseline/model; define/review AOIs; derive scanpaths if needed | event/AOI/sequence tables | [Methods overview](methods-overview.md) | complex model = superior model |
| **7. Validate the estimand** | reference labels + split policy | evaluate on leakage-safe held-out data with matching metrics | held-out predictions + metrics | [Validation guide](validation-evidence-guide.md) | sample accuracy = temporal event quality |
| **8. Audit rate and provenance** | acquisition + analysis-rate history | distinguish native from derived rates and preserve source lineage | rate/sensitivity record | [Sampling sensitivity](sampling-sensitivity.md) | derived 60 Hz = native 60 Hz validity |
| **9. Freeze the evidence bundle** | final analysis outputs | freeze manifests, fingerprints, certificates, code/environment, figures/tables | reconstructable archive | [Publication readiness](publication-readiness.md) | archive completeness = stronger evidence |
| **10. Report qualified claims** | frozen bundle | write methods/results with explicit evidence boundary | manuscript-ready record | [Reproducible reporting](reproducible-reporting.md) | broader claims than the design supports |

## Worked route: a static advertising/interface study

A concrete worked example is available for a hypothetical static advert/interface with four researcher-defined regions:

```text
brand → claim → product → disclosure
```

The bundled script uses deterministic **synthetic, real-data-shaped** gaze and demonstrates source preservation, canonicalisation, QC, transparent I-VT events, fixation centroids, AOI assignment, semantic scanpaths, provenance, and an analysis-plan record.

```bash
python examples/04_worked_advertising_study.py \
  --output-dir worked-advertising-study-demo
```

The example contains **no empirical advertising effect and no model-performance claim**. It exists to show how a domain study can be structured without turning software output into unsupported evidence.

[Open the worked study →](worked-advertising-study.md) · [Browse runnable examples →](runnable-examples.md)

## Decision points worth freezing before analysis

Before you treat the workflow as confirmatory, record at least:

- the participant/trial/stimulus identifiers that define independent units;
- the native acquisition rate and any derived analysis rate;
- the source of AOIs and whether AI proposals were human-reviewed;
- the QC review/exclusion rule and whether it was prespecified;
- the event method, thresholds, model identity, confidence/abstention rule, and training regime;
- the held-out unit and leakage controls;
- the primary metric family that matches the estimand;
- the software version or exact commit SHA; and
- the explicit statement of what the design does **not** establish.

If those decisions are not yet fixed, label them exploratory rather than backfilling certainty after seeing the outputs.

## Keep the layers separate

```text
software can run
      ≠
input is scientifically valid
      ≠
model is validated for this setting
      ≠
substantive interpretation is established
```

That separation is the central reason to keep source data, transformations, predictions, review decisions, validation artifacts, and manuscript claims as distinct records.

Continue with the [Publication-readiness checklist](publication-readiness.md), [Research terminology](research-terminology.md), and [Reproducible reporting](reproducible-reporting.md).
