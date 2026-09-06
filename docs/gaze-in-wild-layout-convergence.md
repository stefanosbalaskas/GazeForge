# Gaze-in-the-Wild layout convergence

This evidence layer answers one narrow recovery question: **what filename and MATLAB-variable layout is supported by the first-author processing code, and is that layout independently reproduced by downstream implementations?**

It does not answer the stronger questions of whether a recovered tree is the original distribution, whether its bytes are authoritative, or whether the dataset files may be analysed or redistributed.

## First-party layout

At pinned first-author repository commit `52262d44e366a53369e10ca73c5f41daf0e8f1e5`, `PlotLabels.m` establishes the processing-code conventions:

```text
PrIdx_%d_TrIdx_%d.mat
PrIdx_%d_TrIdx_%d_Lbr_%d.mat
ProcessData
LabelData
```

The reviewed `PlotLabels.m` Git blob is `511581250e04c62037c71d2da16271be4979d434`.

The same first-author repository's pinned `.gitignore` blob, `85f9e994c92da6cbb5632ab241ae7473a83b35e5`, excludes `.mat` and other data/media products. Combined with the already-frozen repository-history audit, this keeps the processing repository separate from the externally hosted `ProcessData` / `LabelData` distribution.

Accordingly, the verified filename and MATLAB-variable grammar is **authoritative processing-schema evidence**, not an authoritative dataset copy.

## Independent downstream convergence

Three independent downstream repositories were reviewed at immutable commits.

| Source | Pinned revision | Reviewed file | Classification |
| --- | --- | --- | --- |
| DFKI OpenGazeLab | `2c87abb3ed5d3e21ed027252a8fcd4fcfd9bdeee` | `backend/src/preprocess_headmounted/giw.py` | Full filename + `ProcessData` / `LabelData` layout match |
| ACE-DNV | `3142eb4457087743664d96994e952ed784741d1f` | `modules/GiW.py` | Full filename + `ProcessData` / `LabelData` layout match |
| LEO-UMCG Unsupervised Gaze Event Discrimination | `12ff306d8690e483d5e721e18d447fbd0d887e54` | `preprocessing.py` | Raw GIW label-file + `LabelData` corroboration only |

The exact reviewed Git blobs are:

```text
DFKI:     eebf405662caa0657095012d9451b3a0576bb5dc
ACE-DNV:  eb30815510c2e04d4239e06b7b22ffc74c10c595
LEO-UMCG: 7489c5df1ef5f5d7125f14b6b609ab2e170c0d3e
```

Two independent downstream implementations therefore reproduce the full first-party filename/variable layout, while a third independently corroborates reading raw GIW labeller files through `LabelData`.

This convergence increases confidence that the grammar is historically representative of GIW processing. It does **not** demonstrate that any downstream tree or archive is byte-identical to the original distribution.

## Recovery-screening use only

A future recovered candidate may use these conventions as a non-authoritative screening signal. For example, a tree containing plausible `PrIdx_*_TrIdx_*.mat` and `PrIdx_*_TrIdx_*_Lbr_*.mat` paths can be flagged as layout-consistent for human review.

That flag must not become any of the following:

- exact-copy identity;
- first-party source authority;
- original-distribution equivalence;
- dataset-file analysis permission;
- redistribution permission;
- participant or task identity;
- sampling-cadence verification;
- independent-labeller recoverability; or
- empirical-evidence eligibility.

The existing recovery quarantine therefore remains unchanged: file roles remain unclassified until the stronger evidence-gated transition is satisfied.

## Frozen identities

The layout-convergence evidence record is bound to:

```text
first-author repository-history evidence:
800d84d71d1d4b1a07e3b6d07c3bb7093c679284f49db0930a9836d77da30ad3

prior secondary-recovery-lead evidence:
e312079108f8b50ddedd6f361272218fc8665c880b147797aee5bb434ebc8c29

historical distribution-availability evidence:
2400c81a0897fb414285069c368a8a9d96de1d18eb185b1073cf15bb1c8bd1da
```

Frozen layout-convergence evidence fingerprint:

```text
b9c006e7bc367d7a66a4e78577d4d267b488eec298619b7e2e6707468172ac12
```

Reviewed exact-file probe fingerprint:

```text
98d9f5d81bed214248c08dbb3901b548b1ae6849f1fd85a33bec474c6e202943
```

The live workflow re-downloads the exact pinned source files, recomputes their Git blob identities, rechecks the required grammar, binds the probe to all frozen parent evidence, and reruns focused adversarial tests.

## What remains unresolved

This tranche does not obtain an authoritative original or canonical GIW compressed distribution. Dataset-file rights, analysis use, and redistribution remain unresolved. Quarantine exit, source-audit readiness, participant/task mapping, actual distributed-file cadence, independent labeller-stream recovery, human-human agreement, participant-disjoint model validation, cross-dataset validation, GP3 validity, and Frozen Evidence performance claims all remain closed.

The next substantive milestone remains acquisition and independent review of an authoritative `ProcessData` / `LabelData` distribution together with applicable dataset-file reuse terms.
