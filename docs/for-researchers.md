# For researchers

GazeForge is a methods toolkit rather than a domain-specific inference engine. The same auditable layers—canonicalisation, QC, event modelling, AOIs, sequences, validation, and provenance—can support different research designs without pretending that gaze alone reveals an unobserved psychological state.

Use this page to enter the documentation from your **research question** rather than from a software module.

If you want to inspect one complete executable path first, run the [practical end-to-end workflow](practical-workflow.md). If you are planning a full study, use the [Study lifecycle](study-lifecycle.md) to connect acquisition, import, QC, measurement, validation, evidence freezing, and reporting before returning here to adapt the layers to your domain question.

<div class="gf-path-grid" markdown>

<div class="gf-path-card" markdown>

### :material-monitor-eye: HCI & interface research

Use gaze events, semantic interface AOIs, dynamic AOIs, scanpaths, and calibration diagnostics to study **observable allocation and sequence of visual attention** during interaction.

Start with: [Visual diagnostics](visual-diagnostics.md) · [Dynamic AOIs](dynamic-aois.md) · [Event-level evaluation](event-level-evaluation.md)

</div>

<div class="gf-path-card" markdown>

### :material-bullhorn-outline: Advertising & marketing

Map fixations to researcher-defined or reviewed semantic regions such as brand, claim, price, disclosure, product, or call-to-action elements. Use scanpaths and event timing as behavioural process measures without labelling them as emotion or persuasion by default.

Start with: [Worked advertising/interface study](worked-advertising-study.md) · [Visual diagnostics](visual-diagnostics.md) · [Research workflows](research-workflows.md)

</div>

<div class="gf-path-card" markdown>

### :material-map-marker-path: Tourism & destination interfaces

Analyse visual attention to maps, sustainability labels, booking information, warning/risk information, destination imagery, and navigation elements while preserving stimulus and participant identity in the analytic table.

Start with: [Semantic AOIs](dynamic-aois.md) · [Reproducible reporting](reproducible-reporting.md)

</div>

<div class="gf-path-card" markdown>

### :material-school-outline: Educational interfaces

Study observable reading/inspection sequences, transitions between instructional elements, and attention to prompts, diagrams, feedback, or navigation regions. Validate event and AOI processing separately from any learning-outcome interpretation.

Start with: [Learning paths](learning-paths.md) · [Scanpath workflows](research-workflows.md)

</div>

<div class="gf-path-card" markdown>

### :material-eye-outline: General visual-attention studies

Use transparent event baselines, participant-disjoint validation, semantic AOIs, scanpaths, and uncertainty-aware model outputs for task-neutral experimental paradigms.

Start with: [Practical workflow](practical-workflow.md) · [I-VT tutorial](tutorial-ivt-baseline.md) · [Validation status](validation-status.md)

</div>

<div class="gf-path-card" markdown>

### :material-shield-search-outline: Methods & validation research

Compare deterministic and learned event models, inspect probability calibration, evaluate boundary timing, test sampling-rate sensitivity, and freeze evidence with explicit source and split provenance.

Start with: [Validation guide](validation-evidence-guide.md) · [Benchmark guide](benchmark-guide.md) · [Results gallery](results-gallery.md)

</div>

</div>

## Research question → GazeForge layer

| Question | Recommended layer | Typical output | Important boundary |
| --- | --- | --- | --- |
| Are samples/trials technically unusual? | QC | anomaly score, flag, quality summary | flag ≠ invalid sample |
| When do fixations/saccades occur? | eye events | class/probability, event intervals | validate against suitable reference labels |
| Which visible region was inspected? | AOIs | AOI assignment with provenance | AI proposal ≠ human ground truth |
| How does a region move through video? | dynamic AOIs | timestamped/interpolated geometry | no silent extrapolation |
| In what order were semantic regions inspected? | scanpaths | labelled sequences/motifs/embeddings | sequence similarity ≠ cognitive-state diagnosis |
| Can a probabilistic event model be trusted at its confidence values? | calibration | ECE, Brier, calibration table | calibration requires held-out predictions |
| Does a result survive different acquisition/derivation assumptions? | sensitivity | rate × purity/retention summaries | derived rate ≠ native-device validation |
| What assumptions govern unavailable measurements? | missing-data handoff | source registry + mechanism questions + treatment registry | MCAR/MAR/MNAR and treatment choice are not package outputs |
| Can somebody reconstruct the analysis? | provenance | fingerprints, manifests, certificates | preserve exact source/software identity |

## A domain workflow that remains auditable

```text
research question
      │
      ▼
predefined observable construct
      │
      ├── acquisition metadata / participant / trial identity
      ├── canonical gaze + QC evidence
      ├── events with model + confidence metadata
      ├── AOIs with source + review metadata
      └── scanpath / transition structures
      │
      ▼
held-out validation / sensitivity checks
      │
      ▼
statistical model tied to the substantive theory
      │
      ▼
qualified interpretation
```

GazeForge should usually occupy the **measurement and process-data layer** of a domain study. The substantive theory—HCI, consumer behaviour, tourism, education, visual cognition, or another field—still determines the construct definition, experimental design, outcome model, and interpretation.

## From gaze measure to substantive interpretation

Before promoting dwell, fixation count, first-fixation latency, scanpaths, model confidence, or QC output into a domain construct, run the [Measurement & interpretation clinic](measurement-interpretation.md). The worked audit records what is directly observable, what independent outcome or validation evidence is required, which sensitivity checks are justified, and what wording remains unsupported by gaze alone.

## Claims GazeForge does not make for you

Do not convert gaze patterns directly into unsupported claims about:

- emotion, sentiment, liking, persuasion, deception, personality, or diagnosis;
- protected characteristics;
- comprehension or learning without an external outcome/criterion;
- purchase/booking intention without an appropriate measured outcome;
- human ground truth from a vendor or algorithm label;
- native-device validity from a resampled or derived benchmark condition.

The package can help quantify **where, when, how long, in what sequence, with what model confidence, and under what validation design** gaze-related observations occurred. Stronger latent interpretations require independent theoretical and empirical support.

## Before preregistration or data collection

Decide in advance:

1. the observable gaze construct and unit of analysis;
2. tracker/acquisition rate and geometry requirements;
3. QC review/exclusion rules;
4. event algorithm and any threshold/sampling-rate sensitivity plan;
5. AOI source: manual, researcher-defined, AI-proposed + reviewed, or tracked dynamic geometry;
6. validation split unit and reference labels, if a learned model is used;
7. primary gaze outcomes versus exploratory process measures;
8. how uncertainty, missingness source/reason, missing-data assumptions, censoring, and abstention will be represented;
9. which evidence artifacts and software identity will be archived.

Then follow the [Study lifecycle](study-lifecycle.md), use the [Outcome & estimand preregistration clinic](estimand-preregistration.md) before confirmatory modelling, use the [Denominator, exposure & censoring clinic](denominator-exposure-censoring.md) to preserve observation-state mechanics, use the [Missing-data assumptions & treatment handoff](missing-data-assumptions.md) before selecting a missing-data strategy in specialist software, use the [Measurement & interpretation clinic](measurement-interpretation.md) before promoting gaze observables into substantive constructs, use [Reproducible reporting](reproducible-reporting.md) for the final methods record, use the [Reviewer & replication handoff](reviewer-replication-handoff.md) before sharing a frozen archive externally, and use the [Publication-readiness checklist](publication-readiness.md) before final release.
