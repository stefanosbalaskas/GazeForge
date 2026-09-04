# Hollywood2EM source-resolution status

GazeForge treats **locating a canonical distribution**, **verifying an exact current copy**, and **auditing that copy** as three different scientific-provenance steps. This page records what a current public-source resolution pass establishes for Hollywood2EM without upgrading literature evidence into a completed source audit.

The machine-readable checkpoint is:

```text
validation/protocols/hollywood2-source-resolution-2026-09-04.json
```

It is a **source-resolution status record, not empirical evidence**.

## What the publication establishes

The authoritative dataset publication is:

> Ioannis Agtzidis, Mikhail Startsev, and Michael Dorr. *Two hours in Hollywood: A manually annotated ground truth data set of eye movements during movie clip watching*. Journal of Eye Movement Research, 13(4), 2020. DOI: `10.16910/jemr.13.4.5`.

The paper reports approximately 130 minutes of manually annotated gaze from 16 observers viewing 50 test clips and 6 training clips from Hollywood2. The recordings are 500 Hz SMI Hi-Speed 1250 data and the annotation taxonomy includes fixation, saccade, smooth pursuit, and noise.

The paper explicitly identifies the distribution location as:

```text
https://gin.g-node.org/ioannis.agtzidis/hollywood2_em
```

Later replication material for event-detection evaluation independently directs users to the same GIN repository. That gives GazeForge a strong canonical distribution identifier.

## What remains unverified

During the 2026-09-04 resolution pass, GazeForge did **not** independently retrieve and fingerprint the exact current GIN repository copy or inspect repository-level license text from that copy. Therefore the status is:

```text
canonical_distribution_identifier_established_current_copy_unverified
```

with:

- `canonical_distribution_identifier_found=true`;
- `current_retrievable_copy_verified=false`;
- `source_audit_ready=false`;
- `empirical_evidence_created=false`.

This is deliberately narrower than saying that the repository no longer exists or that the dataset is unavailable. The literature establishes the canonical location; exact current retrievability and file identity were not verified in this pass.

## Article license is not silently promoted to dataset license

The Journal of Eye Movement Research article is licensed CC BY 4.0. GazeForge does **not** infer from that fact that every dataset file in the GIN repository is covered by the same license.

A related doctoral thesis describes the Hollywood2EM data as publicly available with an open-source license, but the resolution pass still did not obtain exact repository-level license text for the current copy. Accordingly:

- analysis-use terms remain unresolved;
- raw-data redistribution terms remain unresolved;
- article CC BY is not treated as dataset licensing evidence;
- a general open-source description is not treated as a substitute for exact terms.

Analysis permission and redistribution permission remain separate fields in the eventual source audit.

## Student and expert labels are not independent annotators

The published Hollywood2EM annotation workflow was sequential. Gaze samples were algorithmically pre-labelled, reviewed by a paid novice/student annotator, and then corrected by an expert annotator. The student labels are reported as available.

That makes student-versus-expert comparison scientifically useful as **annotation sensitivity**, but it is not independent human-human reliability. The expert stream is a correction of the earlier work rather than a separately produced annotation of the same samples.

GazeForge therefore keeps:

- `independent_human_annotation_streams_verified=false`;
- student-versus-expert analysis separate from model generalisation;
- neither stream interpreted as an error-free ground truth.

## What must happen next

The source-resolution step materially narrows the remaining work, but it does not close the empirical gate. The next actions are:

1. obtain an exact current copy from the canonical GIN repository or an author-verified institutional copy;
2. verify repository-level analysis-use and raw-data redistribution terms from that exact copy;
3. inventory and SHA-256 fingerprint every expected ARFF file;
4. verify participant and trial identity mapping from the authoritative structure;
5. verify gaze coordinate units before any unit-sensitive Lund↔Hollywood2 modelling;
6. freeze student-versus-expert annotation sensitivity separately;
7. only then run and freeze held-out cross-dataset model validation.

Until those gates pass, Hollywood2EM remains a well-identified external benchmark candidate with **source-audit and empirical execution pending**.

## Public sources used for this checkpoint

- Dataset publication: <https://doi.org/10.16910/jemr.13.4.5>
- Open full-text copy: <https://pmc.ncbi.nlm.nih.gov/articles/PMC8005322/>
- Event-detection evaluation replication repository: <https://github.com/r-zemblys/EM-event-detection-evaluation>
- Doctoral thesis describing the public dataset repositories: <https://mediatum.ub.tum.de/doc/1538004/1538004.pdf>
- Canonical distribution identifier reported by the publication: <https://gin.g-node.org/ioannis.agtzidis/hollywood2_em>

These references document the resolution decision. They do not replace exact-copy audit evidence.
