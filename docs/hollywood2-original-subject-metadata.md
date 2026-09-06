# Hollywood-2 original subject metadata boundary

This tranche freezes what the public original Hollywood-2 distribution currently says
about subject counts, viewing tasks, sampling, access, and reuse terms. It does **not**
turn filename tokens into participant identities and it does **not** authorize dataset use.

## Reviewed public observation

The immutable record is:

`validation/evidence/hollywood2/hollywood2-original-subject-metadata-evidence-v1.json`

It is bound to workflow run `34060071078` on exact head
`9eb7d0da9ae08cbc5d93e68e8a34dc29a159cfd1`, artifact `9997181901`, artifact
SHA-256 `a8c15f0f38b3648786ce331f3cf50d4ad5683be093a0cf0d3505ff12e5529f7e`,
and live probe fingerprint
`1965813fa733a77173d5248fa9d65bf2c2a6b81f33f706cfc2ee076602f99622`.

The reviewed public description stated:

- 16 human volunteers;
- 12 active subjects performing action recognition;
- 4 free-viewing subjects with no specific task;
- 500 Hz recording;
- one advertised Hollywood-2 gaze-data download link.

The description page mentions an included readme, but the reviewed public page exposed no
separate public README link or subject-ID ledger. The advertised
`gaze_hollywood2.zip` route resolved by `HEAD` to
`https://vision.imar.ro/eyetracking/main_login.php` as HTML. The probe did not
authenticate, register, submit an academic request, or download the archive.

The reviewed public license page stated academic-use restrictions, an academic-address
request condition, limited/non-exclusive/non-assignable/non-transferable terms,
no sublicensing/transfer, and a prior-written-permission clause. Merely observing this
page does not accept the terms or establish authorization for GazeForge.

Primary public pages:

- <https://vision.imar.ro/eyetracking/description.php>
- <https://vision.imar.ro/eyetracking/license.php>

## Historical subject-count trap

The public description currently presents the earlier 16-viewer Hollywood-2 distribution.
Later descriptions of *Actions in the Eye* report an expanded 19-subject setup and
scene-context recognition in addition to action recognition and free viewing. This
historical evolution is exactly why subject counts cannot be used to reverse-engineer
participant identities.

Useful publication records:

- <https://arxiv.org/abs/1312.7570>
- <https://www.lunduniversity.lu.se/publication/e4efe293-637e-4466-ac49-c9675eeea446>

The frozen GIN history contains 16 stable three-digit filename prefixes:

`001, 002, 003, 004, 005, 006, 008, 010, 011, 012, 013, 014, 015, 017, 018, 019`

Within `001` through `019`, `007`, `009`, and `016` are absent. The numerical pattern
and the count of 16 are **not** evidence that these tokens correspond one-to-one to the
16 participants on the public original-distribution page, nor do they reveal task groups.

## Fail-closed fresh validation

`validate_hollywood2_original_subject_live_probe()` requires the public subject/task
markers, the single expected data link, the login-gated HTML route, and the reviewed
license markers to remain present. It deliberately stops for manual review if:

- a public README/subject-ledger link appears;
- the advertised archive route becomes a direct archive or changes away from the
  reviewed login gate;
- the subject/task markers change;
- the license markers change; or
- any rights, participant-mapping, or scientific-validation flag is promoted.

A newly public archive, README, or mapping surface is new evidence to inspect. It is
never treated as automatic permission to download, redistribute, map participants, or
create participant-disjoint validation.

## Still unresolved

This tranche does **not** resolve:

- authoritative original subject IDs or subject-to-task-group ledger;
- GIN filename token to original subject identity;
- GIN filename token to viewing/task group;
- dataset-access authorization for this project;
- redistribution authorization;
- participant-disjoint modelling;
- source-audit readiness;
- Lund-to-Hollywood2 cross-dataset validation; or
- any new empirical performance claim.

Closing those gates requires an authoritative included README/subject ledger or explicit
author/source clarification, plus the separate rights and empirical validation steps.
