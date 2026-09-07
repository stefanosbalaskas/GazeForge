# Gaze-in-the-Wild distributed-overlap human-human agreement

GazeForge now has a frozen **human-human annotation agreement baseline for the verified multi-labeller overlap subset** of the original Gaze-in-the-Wild `LabelData` distribution.

This is deliberately narrower than a full-dataset benchmark. It does **not** validate a GazeForge model, Gazepoint GP3 hardware, gaze coordinates, participant-disjoint prediction, cross-dataset generalization, or the unresolved mapping from distribution `TrIdx` tokens to publication task names.

## Verified analysis set

The original `LabelData` distribution contains 50 files and 37 distribution-native recording tokens. Structural inspection found five recordings with multiple distributed human labellers and exact within-recording timestamp compatibility:

- `PrIdx_1_TrIdx_1`
- `PrIdx_1_TrIdx_2`
- `PrIdx_2_TrIdx_1`
- `PrIdx_2_TrIdx_2`
- `PrIdx_6_TrIdx_2`

`PrIdx` and `TrIdx` are used here only as verified distribution-native identifiers. No publication task name is assigned to any `TrIdx`.

The reviewed HHA subset contains 18 original `LabelData` files totaling **10,274,311 bytes**. Every file was re-downloaded from the frozen Figshare source, matched to its prior size, MD5, and SHA-256 identity, checked for agreement between filename tokens and internal `PrIdx`/`TrIdx`/`LbrIdx`, and deleted after inspection. No raw MAT data is retained in the repository or workflow artifact.

## Pre-specified agreement protocol

The protocol was fixed before the HHA values were observed:

- **All-label sample agreement:** exact agreement and Cohen's kappa across the complete aligned timestamp stream, including label code 0 (`unlabelled`).
- **Pairwise-clearly-labelled sample agreement:** the same metrics after retaining only timestamps for which both selected humans supplied a nonzero label.
- **Event agreement:** code 0 remains a hard event separator but is not an event class; events require the same class and temporal IoU >= 0.50.
- **Bidirectional evaluation:** each human is used as reference in turn; neither annotator is treated as ground truth.
- Sampling cadence is inferred independently from each recording's exact timestamps.
- No resampling, gaze coordinates, or `ProcessData` are used.

The human event vocabulary in the source labels is fixation, pursuit, saccade, blink, VOR, plus code 0/unlabelled at sample level.

## Frozen pairwise results

| Labellers | Shared recordings | Aligned samples | Clearly labelled fraction | All-label agreement | All-label kappa | Clear agreement | Clear kappa | Event F1 | Mean matched IoU |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1-2 | 4 | 371,723 | 0.572 | 0.847 | 0.792 | 0.872 | 0.815 | 0.768 | 0.811 |
| 1-5 | 4 | 371,723 | 0.574 | 0.853 | 0.801 | 0.891 | 0.842 | 0.754 | 0.816 |
| 1-6 | 4 | 371,723 | 0.566 | 0.838 | 0.781 | 0.878 | 0.825 | 0.676 | 0.793 |
| 2-5 | 4 | 371,723 | 0.555 | 0.891 | 0.848 | 0.891 | 0.840 | 0.756 | 0.831 |
| 2-6 | 4 | 371,723 | 0.546 | 0.880 | 0.833 | 0.890 | 0.841 | 0.719 | 0.834 |
| 5-6 | 5 | 432,444 | 0.507 | 0.881 | 0.830 | 0.891 | 0.844 | 0.701 | 0.810 |

Across the six human pairs:

- all-label exact agreement ranges from **0.838 to 0.891**;
- all-label Cohen's kappa ranges from **0.781 to 0.848**;
- pairwise-clearly-labelled exact agreement ranges from **0.872 to 0.891**;
- pairwise-clearly-labelled kappa ranges from **0.815 to 0.844**;
- bidirectional event F1 ranges from **0.676 to 0.768**;
- mean matched event IoU ranges from **0.793 to 0.834**.

These values quantify disagreement among the available distributed human annotations. They are therefore a useful empirical reference for later model evaluation, but **they are not model-performance values themselves**.

## Event-matching scalability correction

The first full HHA attempt exposed a computational issue in the generic event matcher: a dense event-by-event Hungarian matrix was correct but unnecessarily large for long non-overlapping temporal streams. The matcher was replaced with an exactly equivalent sparse implementation that enumerates only positive temporal-overlap edges, decomposes those edges into independent bipartite components, and applies the same maximum-total-IoU Hungarian objective within each component.

Before re-running HHA, the sparse matcher was checked against a literal dense reference implementation across deterministic randomized interval streams, both label policies, multiple IoU thresholds, tie cases, disconnected components, and a 5,000-by-5,000 sequential-event scalability regression. The dedicated HHA step then completed in 63 seconds instead of exceeding the former 20-minute workflow limit.

## Reproducibility binding

The reviewed empirical result is bound to:

- workflow run: `34170510919`
- workflow job: `101889768746`
- exact workflow head: `94996d99010ca5ed5f988bcb60cebb053923ffc2`
- artifact ID: `10035567001`
- artifact ZIP SHA-256: `67bebc822a3633b03e81914c542abb78c64c1e75d42c13a95be60dfd3ad4f87c`
- discovery fingerprint: `ed0af8abff6d235c71810f3964dc0c9a3dafd33d8260415e333d199da5713569`
- selected-file verification manifest: `b93b8a89b5cc72c057973bddeccb17f15114afa7865d44ddf460b9762dd85c0a`
- reviewed HHA evidence fingerprint: `7e6d6180b01417d7be2e07483cc0c7e0feb86a1d08be6b8aeba03f48fdb27f02`

The frozen evidence is stored at:

`validation/evidence/gaze-in-wild/gaze-in-wild-distributed-overlap-human-human-agreement-evidence-v1.json`

and is validated fail-closed by `gazeforge.gaze_in_wild_overlap_hha_evidence`.

## Scientific boundary

This tranche establishes exactly one new empirical fact: **human-human agreement exists and has been quantified for the five-recording distributed overlap subset**.

The following remain unverified or deliberately closed:

- full-distribution HHA across all 50 `LabelData` files / 37 recording tokens;
- task-stratified HHA;
- a complete file-to-publication-task mapping;
- gaze-coordinate validation in this HHA analysis;
- participant-disjoint GazeForge model validation on GIW;
- cross-dataset validation;
- native Gazepoint GP3 validity;
- quarantine exit;
- any new GazeForge model-performance claim.
