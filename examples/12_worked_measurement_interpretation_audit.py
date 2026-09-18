"""Deterministic teaching bundle for auditing gaze-measure interpretation.

This example performs no scientific inference. It makes observable-to-construct
bridges, validity threats, sensitivity checks, and reporting limits explicit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

EVIDENCE_CLASSIFICATION = "synthetic_demo_not_empirical_evidence"
ALLOWED_STATUSES = (
    "observable_supported",
    "requires_external_outcome",
    "requires_measurement_validation",
    "requires_sensitivity_analysis",
    "not_supported_by_gaze_alone",
)


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _claims() -> pd.DataFrame:
    rows = [
        ("C01", "The claim AOI received 920 ms of observed fixation dwell.", "claim_aoi_dwell_ms", "visual inspection", "observable_supported", "none for the descriptive dwell statement"),
        ("C02", "Longer claim dwell shows greater trust.", "claim_aoi_dwell_ms", "trust", "requires_external_outcome", "independent trust measure plus task-specific theory"),
        ("C03", "The disclosure was fixated earlier than the product.", "first_fixation_latency_ms + event_observed", "relative time-to-first fixation", "requires_sensitivity_analysis", "censoring-aware comparison and stable AOI/event definitions"),
        ("C04", "More fixations prove stronger interest.", "fixation_count", "interest", "not_supported_by_gaze_alone", "independent interest measure and construct-validation evidence"),
        ("C05", "The scanpath demonstrates a persuasion strategy.", "semantic_scanpath / transitions", "persuasion strategy", "not_supported_by_gaze_alone", "independent behavioural/theoretical evidence"),
        ("C06", "A 0.92 model confidence means the label is correct.", "model_probability", "prediction correctness", "requires_measurement_validation", "held-out labels, discrimination, calibration, and coverage"),
        ("C07", "A QC flag identifies an invalid observation.", "qc_flag / anomaly_score", "scientific invalidity", "requires_measurement_validation", "review protocol or independently validated decision rule"),
        ("C08", "Derived 60 Hz performance validates native 60 Hz acquisition.", "derived_rate_validation_result", "native-device validity", "not_supported_by_gaze_alone", "native target-device acquisition and suitable reference labels"),
    ]
    return pd.DataFrame(rows, columns=[
        "claim_id", "intended_statement", "observable", "proposed_construct",
        "status", "external_evidence_required",
    ])


def _measurements() -> pd.DataFrame:
    rows = [
        ("AOI dwell_ms", "sum of observed fixation duration assigned to a frozen AOI", "participant × trial × AOI", "0 only when observable and no dwell occurred; missing remains missing", "descriptive allocation of observed fixation time", "AOI provenance; event definition; coverage", "trust; persuasion; interest; comprehension; preference", "api-reference.md#semantic-aois", "04_trial_aoi_metrics.csv"),
        ("fixation_count", "count of declared fixation events in the analysis unit", "participant × trial × AOI", "preserve missing trial/AOI exposure; do not coerce unavailable rows to zero", "descriptive event frequency under a fixed detector", "event detector; AOI assignment; exposure", "interest; difficulty; engagement; cognitive effort", "api-reference.md#eye-events; api-reference.md#semantic-aois", "04_trial_aoi_metrics.csv"),
        ("first_fixation_latency_ms", "time from declared trial origin to first observed AOI fixation", "participant × trial × AOI", "no fixation is right-censored at observable trial time; it is not latency=0", "time-to-first observed AOI fixation", "trial origin; exposure; event indicator; censor time", "noticeability; salience; preference; memory", "api-reference.md#eye-events; api-reference.md#semantic-aois", "04_trial_aoi_metrics.csv"),
        ("event duration / boundaries", "duration and onset/offset under the declared event method", "event nested in participant × trial", "ambiguous/unobserved intervals remain explicit", "temporal event structure", "timebase; detector identity; validation where claimed", "physiological truth of the event definition", "api-reference.md#eye-events", "02_reviewed_event_intervals.csv / 05_trial_event_metrics.csv"),
        ("scanpath / transitions", "ordered semantic AOI labels from reviewed fixation assignments", "participant × trial sequence", "unassigned/missing states follow an explicit policy", "descriptive sequence/transition structure", "AOI provenance; sequence rule; repeat/unassigned policy", "strategy; persuasion; comprehension; intent; diagnosis", "api-reference.md#scanpaths", "13_semantic_scanpaths.csv"),
        ("model confidence / probability", "probability-like output from the declared learned model", "sample/event as declared", "abstentions remain explicit and coverage is reported", "uncertainty-aware model output after held-out evaluation", "reference labels; held-out design; calibration; coverage", "correctness of an individual label", "api-reference.md#structural-validation-scope", "held-out prediction/calibration outputs"),
        ("QC / coverage / data loss", "declared quality diagnostic or observed/usable proportion", "explicit sample/trial/participant/stream unit", "retain original denominator and separate decision layer", "quality review and sensitivity description", "QC method; denominator; thresholds; review rule", "scientific invalidity of an observation", "api-reference.md#quality-control", "pre-review QC + review ledger + denominator flow"),
        ("sampling-rate / derivation status", "native/nominal rate, observed cadence, and any derived rate", "acquisition stream / analysis condition", "keep rate identities distinct", "sampling provenance and rate sensitivity", "acquisition record; timestamp diagnostic; derivation rule", "native-device validity from a derived-rate condition", "api-reference.md#sampling-sensitivity", "source contract + sampling-sensitivity outputs"),
    ]
    return pd.DataFrame(rows, columns=[
        "measure", "observable_definition", "unit_of_analysis", "missing_zero_censoring",
        "possible_use", "requires", "do_not_infer_automatically", "api_reference", "artifact",
    ])


def _threats() -> pd.DataFrame:
    rows = [
        ("V01", "construct bridge", "observable promoted to latent construct without independent evidence", "measure the construct independently or restrict the claim"),
        ("V02", "event definition", "result depends on detector/model/threshold", "report identity and justified sensitivity"),
        ("V03", "AOI definition", "geometry/semantics/overlap change the outcome", "freeze AOIs and evaluate justified perturbations"),
        ("V04", "sampling/timebase", "native, observed, and derived rates are conflated", "retain rate identity and rate-sensitivity evidence"),
        ("V05", "data quality", "missingness/data loss differs across conditions", "report denominators/coverage and sensitivity"),
        ("V06", "exclusion", "review choices change the analysis population", "retain pre-review evidence and decision ledger"),
        ("V07", "inferential unit", "samples/fixations are treated as independent participants", "preserve repeated-measures grouping"),
        ("V08", "censoring", "no-fixation latency is deleted or encoded as zero", "retain event indicator/censor time"),
        ("V09", "generalisation", "task/device-specific evidence is described as universal", "name held-out/generalisation unit"),
        ("V10", "researcher degrees of freedom", "many outcomes/thresholds explored without status labels", "prespecify primary outcomes; label exploratory analyses"),
    ]
    return pd.DataFrame(rows, columns=["threat_id", "area", "threat", "mitigation"])


def _sensitivity() -> pd.DataFrame:
    rows = [
        ("S01", "AOI boundary perturbation", "recompute affected metrics under prespecified geometry perturbations"),
        ("S02", "event detector/threshold", "compare justified variants without selecting the most favourable"),
        ("S03", "quality/exclusion", "repeat under prespecified review/exclusion sensitivity rules"),
        ("S04", "sampling derivation", "compare supported rates while preserving derivation provenance"),
        ("S05", "coverage/exposure", "inspect results against coverage and denominator changes"),
        ("S06", "latency censoring", "retain no-fixation cases and use censoring-aware analysis"),
        ("S07", "split identity", "evaluate only under explicitly supported held-out units"),
    ]
    return pd.DataFrame(rows, columns=["sensitivity_id", "check", "procedure"])


def _language() -> pd.DataFrame:
    rows = [
        ("R01", "Participants trusted the claim because they looked longer.", "Participants showed greater observed dwell on the claim AOI; trust requires an independent measure.", "AOI dwell is visual inspection, not trust by itself."),
        ("R02", "The disclosure was never noticed.", "No disclosure fixation was observed within the available exposure.", "No observed fixation is not proof of no awareness."),
        ("R03", "No-fixation trials had zero latency.", "No-fixation trials were retained as right-censored.", "Zero latency means an event at time origin, not no event."),
        ("R04", "The QC model removed invalid gaze.", "QC outputs were review evidence; exclusions followed the recorded rule.", "A QC flag is not scientific invalidity."),
        ("R05", "The model was 92% confident, therefore correct.", "The model emitted 0.92 confidence; correctness/calibration were evaluated separately.", "Individual confidence is not correctness."),
        ("R06", "The model was validated at native 60 Hz.", "The model was evaluated on a derived 60 Hz condition under the reported rule.", "Derived-rate evidence is not native-device validation."),
    ]
    return pd.DataFrame(rows, columns=["report_id", "avoid", "prefer", "limitation"])


def _readme() -> str:
    return """# Worked measurement & interpretation audit

This deterministic teaching bundle makes claim boundaries explicit. It performs no
inferential statistics and never decides whether a psychological construct is validly
measured.

Statuses are workflow prompts, not truth labels. The bundle never labels a scientific
claim `valid` or `invalid`, never infers a latent state from gaze alone, never
converts missing values to zero, and never converts a no-fixation latency into zero.

Evidence class: `synthetic_demo_not_empirical_evidence`.
"""


def run(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    claims, measurements = _claims(), _measurements()
    threats, sensitivity, language = _threats(), _sensitivity(), _language()

    tables = {
        "01_claim_registry.csv": claims,
        "02_measurement_interpretation_matrix.csv": measurements,
        "03_validity_threats.csv": threats,
        "04_sensitivity_plan.csv": sensitivity,
        "05_reporting_language.csv": language,
    }
    for name, table in tables.items():
        table.to_csv(output_dir / name, index=False)
    (output_dir / "README.md").write_text(_readme(), encoding="utf-8")

    statuses = set(claims["status"].astype(str))
    if not statuses <= set(ALLOWED_STATUSES):
        raise RuntimeError("Unexpected interpretation-audit status.")
    if {"valid", "invalid"} & {status.lower() for status in statuses}:
        raise RuntimeError("Truth-label statuses are prohibited.")

    latency = measurements.loc[measurements["measure"] == "first_fixation_latency_ms"].iloc[0]
    if "right-censored" not in latency["missing_zero_censoring"]:
        raise RuntimeError("No-fixation latency must retain censoring semantics.")

    data_files = [output_dir / name for name in tables] + [output_dir / "README.md"]
    _write_json(output_dir / "interpretation_audit.json", {
        "example": "12_worked_measurement_interpretation_audit",
        "evidence_classification": EVIDENCE_CLASSIFICATION,
        "allowed_statuses": list(ALLOWED_STATUSES),
        "claim_count": int(len(claims)),
        "measurement_family_count": int(len(measurements)),
        "validity_threat_count": int(len(threats)),
        "sensitivity_check_count": int(len(sensitivity)),
        "reporting_example_count": int(len(language)),
        "artifact_hashes_sha256": {path.name: _sha256(path) for path in data_files},
        "automatic_construct_inference_performed": False,
        "causal_claim_created": False,
        "psychological_state_claim_created": False,
        "inferential_statistics_created": False,
        "estimator_selected": False,
        "missing_converted_to_zero": False,
        "no_fixation_latency_converted_to_zero": False,
        "claim_truth_labels_created": False,
        "scientific_boundary": (
            "Manual interpretation-audit teaching scaffold only; construct validity "
            "requires theory and evidence external to gaze-derived observables."
        ),
    })

    print("Worked measurement/interpretation audit complete")
    print(f"Output directory: {output_dir}")
    print(f"Claims audited: {len(claims)}")
    print("Automatic construct inference: no")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a deterministic gaze measurement/interpretation audit scaffold."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("worked-measurement-interpretation-audit"),
    )
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()
