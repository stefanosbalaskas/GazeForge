# Study-design templates

These templates are deliberately explicit. Replace every placeholder with a study-specific value; do **not** let software, documentation, or later analysts silently guess units, sampling rate, screen geometry, identity, split design, or evidence strength.

!!! warning "A completed template is not validation"
    The templates make assumptions auditable. They do not establish device validity, construct validity, threshold validity, label validity, or generalizability.

## Preregistration / analysis-plan record

```yaml
study_id: <stable study identifier>
research_question: <observable question>
primary_estimand: <what quantity is estimated>
primary_unit_of_analysis: <sample | event | fixation | trial | participant | other>
stimulus_scope: <static image | interface | video | mixed>
primary_outcome_definition: <explicit operational definition>
secondary_outcomes: <list or none>
planned_aoi_labels: <list or none>
planned_event_method: <I-VT | angular I-VT | learned model | other>
planned_qc_review_rule: <explicit rule>
planned_exclusion_rule: <explicit rule; no silent deletion>
planned_validation_design: <if applicable>
planned_sensitivity_analyses: <list>
scientific_boundary: <what the design will not establish>
```

## Acquisition metadata record

```yaml
tracker_vendor: <value>
tracker_model: <value>
tracker_firmware_or_software: <value or unknown>
native_sampling_rate_hz: <value>
observed_timestamp_cadence_hz: <value and how estimated>
timestamp_unit: <ms | s | other>
coordinate_basis: <pixels | normalized | other>
screen_width_px: <value>
screen_height_px: <value>
viewing_distance_cm: <value or not measured>
calibration_protocol: <points / acceptance rule / rerun rule>
participant_identity_field: <source field>
trial_identity_field: <source field>
stimulus_identity_field: <source field>
synchronization_method: <if video/physiology/multimodal>
source_file_identity: <path / immutable ID / checksum>
```

Keep **native sampling rate** separate from the **observed timestamp cadence**. Supplying a nominal rate to a function does not validate timestamp regularity.

## QC and exclusion protocol

```yaml
qc_method: <method>
qc_parameters: <explicit parameters>
random_seed: <value or not applicable>
missingness_definition: <explicit>
offscreen_definition: <explicit>
gap_definition: <explicit>
anomaly_flag_definition: <explicit>
reviewer_role: <who reviews flags>
automatic_deletion: false
exclusion_unit: <sample | event | trial | participant | none>
exclusion_rule: <explicit rule>
exclusion_decision_log: <artifact path>
sensitivity_analysis_for_exclusions: <yes/no + details>
```

**QC flags are review signals, not automatic proof that samples are invalid.** If an exclusion is made, preserve the rule and decision separately from the original empirical record.

## AOI provenance and review record

```yaml
stimulus_id: <value>
aoi_mode: <static | dynamic>
aoi_definition_source: <researcher | model proposal | imported annotation>
aoi_labels: <list>
geometry_unit: <pixels | normalized | other>
overlap_rule: <first | smallest_area | highest_confidence | other>
dynamic_keyframe_times_ms: <list or not applicable>
max_interpolation_gap_ms: <value or not applicable>
extrapolation_allowed: false
model_name: <if AI-proposed>
model_version: <if AI-proposed>
proposal_confidence_field: <field or not applicable>
reviewer: <role/identifier>
review_decision_field: <accepted/rejected/edited/relabelled>
reviewed_aoi_artifact: <path/checksum>
```

For dynamic AOIs, bounded interpolation does not authorize temporal extrapolation. Preserve unresolved timestamps rather than inventing geometry beyond the observed track.

## Validation split and reference-label record

```yaml
prediction_target: <event class | AOI geometry | assignment | other>
reference_label_source: <annotator/corpus/protocol>
reference_label_rate_hz: <value>
reference_label_status: <native | derived | mixed>
held_out_unit: <participant | stimulus | dataset | source token | other>
n_folds: <value>
group_identity_field: <field>
participant_disjoint: <true/false/unknown>
stimulus_disjoint: <true/false/unknown>
dataset_held_out: <true/false>
source_token_disjoint: <true/false>
leakage_check: <method/artifact>
matched_rows_across_models: <true/false>
sample_level_metrics: <list>
event_level_metrics: <list>
calibration_metrics: <list or not applicable>
```

If only an opaque source token is known, report **source-token-disjoint**. Do not promote it to participant-disjoint unless an authoritative token→participant mapping exists.

## Native-versus-derived sampling statement

```yaml
acquisition_rate_hz: <value>
analysis_rate_hz: <value>
analysis_rate_status: <native | derived>
resampling_method: <method or none>
label_purity_rule: <rule or none>
timestamp_cadence_check: <method/result>
device_specific_validity_claim: <none unless separately supported>
```

Copy-ready wording for a derived condition:

> The analysis used a derived `<analysis_rate_hz>` Hz condition constructed from native `<acquisition_rate_hz>` Hz data using `<resampling_method>` and `<label_purity_rule>`. This condition is not presented as native `<analysis_rate_hz>` Hz device validation.

## Reproducibility / archive manifest

```yaml
software_name: gazeforge
software_version: <version>
software_commit: <full SHA when using development code>
python_version: <value>
environment_lock: <requirements/lock file>
source_fingerprint: <SHA-256>
canonical_table_fingerprint: <SHA-256>
analysis_table_fingerprint: <SHA-256>
aoi_artifact_fingerprint: <SHA-256 or not applicable>
model_artifact_identity: <path/hash or not applicable>
random_seeds: <list>
analysis_plan_path: <path>
provenance_path: <path>
figure_inventory: <list>
table_inventory: <list>
evidence_classification: <classification>
archive_doi_or_persistent_id: <value when frozen>
scientific_boundary: <explicit limitation>
```

## Methods minimum record

A manuscript Methods section should allow a reader to reconstruct the analytic identity of the result. At minimum record:

```text
Software: GazeForge <version>; development commit <full SHA if applicable>.
Acquisition: <tracker/model>, native <rate> Hz; observed cadence <rate/method>.
Display: <width × height px>; coordinates <basis>; timestamps <unit>.
Identity: participant=<field>; trial=<field>; stimulus=<field>.
QC: <method + parameters>; flags reviewed under <rule>; exclusions=<rule/count>.
Events: <method/model + parameters + training provenance>.
AOIs: <static/dynamic + source + review + overlap/interpolation policy>.
Validation: <held_out_unit>, <folds>, leakage check <method>.
Sampling status: <native/derived>; resampling/purity <rule>.
Metrics: <sample-level>; <event-level>; <calibration if relevant>.
Archive: source_fingerprint=<hash>; software_commit=<hash>; provenance=<artifact>.
Boundary: <what the analysis does not establish>.
```

## Recommended artifact folder

```text
study/
├── 00_source/
│   ├── immutable_exports/
│   └── source_checksums.csv
├── 01_design/
│   ├── preregistration.yaml
│   └── acquisition_metadata.yaml
├── 02_qc/
│   ├── qc_samples.csv
│   ├── trial_quality.csv
│   └── exclusion_decisions.csv
├── 03_aoi/
│   ├── aoi_definitions.csv
│   └── aoi_review.csv
├── 04_models/
│   ├── fold_assignments.csv
│   └── model_identity.json
├── 05_analysis/
│   ├── analysis_tables/
│   └── provenance.json
└── 06_freeze/
    ├── workflow_manifest.json
    ├── environment-lock.txt
    └── publication-readiness.md
```

The exact folder names are optional. The important property is separation of immutable source material, review decisions, derived analytic artifacts, and frozen publication outputs.

## Pair with the reporting guide

Use [Reproducible reporting](reproducible-reporting.md) for claim-safe manuscript wording, [Research recipes](research-recipes.md) for task-first routes, and [Publication readiness](publication-readiness.md) for the final pre-submission audit.
