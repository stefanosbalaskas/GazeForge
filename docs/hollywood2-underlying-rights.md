# Hollywood2 underlying source and rights

GazeForge now freezes a second, separate provenance layer for Hollywood2EM: the institutional source and licence context of the **original Mathe–Sminchisescu Hollywood-2 eye-movement distribution**. This is deliberately distinct from the later **Agtzidis–Startsev–Dorr Hollywood2EM hand-labelled GIN repository**.

## What is verified

The institutional *Actions in the Eye* site currently verifies the original Hollywood-2 recording context as:

- 16 participants in total;
- 12 active action-recognition participants and 4 free-viewing participants;
- SMI iView X HiSpeed 1250 recording at 500 Hz;
- a 1280 × 1024 display measuring 47.5 × 29.5 cm;
- 60 cm viewing distance.

The current institutional licence page states an academic-use-only grant. The standard grant is limited, non-exclusive, non-assignable, and non-transferable; use requires citation of the Mathe–Sminchisescu Hollywood-2 eye-movement papers; uses outside the permitted academic scope require separate permission.

The frozen evidence therefore records:

- `analysis_use_terms_status = verified_academic_use_only` for the **underlying Hollywood-2 gaze distribution**;
- `raw_archive_redistribution_status = not_permitted_under_standard_grant` for that same underlying distribution.

These statements do **not** convert the article's CC BY licence into a dataset licence.

## Current distribution endpoint

The institutional description page publishes the archive name `gaze_hollywood2.zip` through:

`http://vision.imar.ro/eyetracking/getdata.php?filepath=data&filename=gaze_hollywood2.zip`

The live 2026-09-05 probe found that this endpoint redirects to the HTTPS login page:

`https://vision.imar.ro/eyetracking/main_login.php`

GazeForge did not authenticate, did not download the 1.8 GiB archive, and did not claim an archive manifest. The current state is therefore **institutional distribution resolved, anonymous direct archive access not verified**.

## Why the GIN annotation rights remain unresolved

The authoritative Hollywood2EM GIN revision remains pinned to:

`870fa6d6209c9085260918d61433a0a2c70fd497`

No `LICENSE` or `COPYING` file was recovered from that repository revision. The original Hollywood-2 licence is not automatically inherited by the later hand-labelled annotation repository. Consequently, GazeForge still records both GIN analysis-use terms and GIN raw-data redistribution terms as unresolved.

## Participant mapping remains open

The institutional source verifies 16 participants and the GIN ground-truth tree exposes 16 filename subject tokens:

`001, 002, 003, 004, 005, 006, 008, 010, 011, 012, 013, 014, 015, 017, 018, 019`

The matching count is useful corroboration but is **not** an authoritative token-to-participant mapping. GazeForge therefore still blocks participant-held-out Hollywood2 modelling and Lund↔Hollywood2 cross-dataset validation until the token semantics are resolved from an authoritative source or archive structure.

## Frozen identities

- Evidence record: `validation/evidence/hollywood2/hollywood2-underlying-source-rights-evidence-v1.json`
- Evidence fingerprint: `6227045c3cc831b3669b34ca74b955847df4b26fafbf825c9a1b5473e25bc943`
- Live probe fingerprint: `1face6d676270165134f34a7956bf848d6422b69dbbfc2e2ecfdb9ac64688707`
- Institutional description raw SHA-256: `305c5f6d7f977d419d40e60509f5b1ce7cdf58d57f91e8710313cb178493d6fe`
- Institutional licence raw SHA-256: `a50bc0cc3f422f6220798acac9991d3c18cbec0533d5d9cfe88554690abfdc2f`

The live workflow re-fetches these institutional pages and fails closed on source or rights drift.
