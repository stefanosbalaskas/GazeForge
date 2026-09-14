# Evidence status

This page is generated from versioned evidence policy and exact repository artifacts. Status is not inferred from whether a model metric looks favourable.

**Status bundle fingerprint:** `64a7be9cbe165a5079c93da85aaeb93a0e997b9c3a0b12443c51c3069eff2913`

| Dataset / target | Status | Evidence scope | Sampling origin |
| --- | --- | --- | --- |
| **Gaze-in-the-Wild** | Reviewed empirical evidence | external participant-disjoint task-agnostic event validation | derived-60hz |
| **Hollywood2EM** | Frozen empirical evidence | external source-token-held-out event validation | resampled |
| **Lund2013** | Frozen empirical evidence | external expert-labelled event validation | mixed-native-and-derived |
| **Native 60 Hz / GP3-class validation** | Empirical execution pending | native device validation | native-60hz-required |
| **VISUS public derivative** | Bounded empirical evidence | partial public derivative empirical analysis | native-tobii-60hz-partial |

## Dataset boundaries

### Gaze-in-the-Wild

**Reviewed empirical evidence.** Reviewed exact-distribution participant-disjoint event-model evidence on a derived 60 Hz task-agnostic analysis grid.

- Reference strength: `human-reference`
- Versioned source: `validation/evidence/gaze-in-wild/gaze-in-wild-exact-participant-disjoint-model-validation-evidence-v1.json`
- Bound evidence fingerprint: `b2fe85ec7e5d5cd425c0cd2593742bab835686c3f560d8a6c06e9c6d67dc547a`
- Open boundaries:
  - Complete authoritative TrIdx-to-task mapping remains unresolved; task-stratified claims remain blocked.
  - The 60 Hz grid is derived rather than native 60 Hz/Gazepoint GP3 validation.
  - Cross-dataset validation and quarantine exit remain unauthorized.

### Hollywood2EM

**Frozen empirical evidence.** Frozen aggregate derived-60-Hz performance on source-token-held-out folds; the split unit is not a verified participant identity.

- Reference strength: `derived-human-reference`
- Versioned source: `validation/evidence/hollywood2/hollywood2-source-token-60hz-frozen-summary-v1.json`
- Bound evidence fingerprint: `e1f1c030f843e118ebd65520dfab8e872efb4ea3e1d520299a993b0ca00ddabf`
- Open boundaries:
  - Exact annotation-repository licence identifier/text and dataset-specific analysis terms remain unresolved.
  - Source-token-held-out evidence is not participant-held-out evidence.
  - Native 60 Hz or Gazepoint GP3 validity is not established.

### Lund2013

**Frozen empirical evidence.** Frozen external expert-labelled event-validation suite; 60 Hz model evidence is derived from native 500 Hz recordings.

- Reference strength: `expert-human-reference`
- Versioned source: `validation/evidence/lund2013/lund2013-suite-manifest.json`
- Bound evidence fingerprint: `5dc6d6336b505b0a2283fe64d478a27b0394c9568a86fc4eb4d2771b8d600f93`
- Open boundaries:
  - Derived 60 Hz results do not establish native 60 Hz or Gazepoint GP3 validity.

### Native 60 Hz / GP3-class validation

**Empirical execution pending.** Native 60 Hz/GP3-class expert-labelled event validation remains an explicit scientific requirement.

- Reference strength: `expert-human-reference-required`
- Open boundaries:
  - No native 60 Hz/GP3-class expert-labelled event corpus has yet cleared the frozen empirical validation gate.

### VISUS public derivative

**Bounded empirical evidence.** Verified partial empirical evidence from public VISUS-supervised derivative Tobii 60 Hz files; no full-dataset model-validation or Frozen Evidence claim.

- Reference strength: `bounded-empirical-observation`
- Versioned source: `validation/evidence/visus-public-partial/visus-public-partial-evidence-v1.json`
- Bound evidence fingerprint: `80e008228e39c2b17bae99a526e2a0157c2c850ebe803c5a370abe9167efde14`
- Open boundaries:
  - Only a partial public derivative is covered; the original 25-participant × 11-stimulus VISUS benchmark is not recovered.
  - Original source licence remains unresolved.
  - No model-validation, human-human-agreement, Frozen Evidence, or native Gazepoint GP3 claim is created.

## Interpretation rule

A stronger status requires an explicit reviewed policy update plus integrity-valid evidence. Missing, malformed, byte-changed, fingerprint-mismatched, or scientifically incompatible evidence fails closed during site generation. Synthetic/demo outputs are never promoted into empirical evidence, derived 60 Hz remains distinct from native 60 Hz/GP3 validation, and source-token-held-out designs remain distinct from participant-held-out designs.
