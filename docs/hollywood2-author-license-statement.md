# Hollywood2EM author license statement

GazeForge freezes an additional **author-authored rights-context signal** for the Hollywood2EM GIN repository. This evidence is stronger than inferring rights from the article licence, but it is deliberately weaker than an exact dataset-license resolution.

## Institutional source

The source is Ioannis Agtzidis's 2020 Technical University of Munich doctoral dissertation, *Towards a better understanding of eye movements in natural contexts*.

A live GitHub Actions probe downloads the institutional PDF, extracts its text with `pdftotext`, and verifies the relevant Chapter 4 statement and repository footnotes. The frozen source identity is:

- PDF size: **44,587,570 bytes**;
- PDF SHA-256: `f91705cafac65facf42563d6b3827148ef4114276759466a26afbc21ff4006ee`;
- normalized extracted-text SHA-256: `2e283d1f9f9f886c07f6629908f1cddc08b7d91fb1de76f50203b07e88974430`;
- live-probe fingerprint: `f99aadc6e0c3bb694fe63321aeacd8f9203868e3b611c99e98b85ebbaafa0a47`.

## What the dissertation verifies

Chapter 4 describes its presented data as publicly available with an **open-source license**. The same chapter footnotes the Hollywood2EM repository at:

`https://gin.g-node.org/ioannis.agtzidis/hollywood2_em`

That footnote is bound to GazeForge's already-audited canonical repository:

`https://gin.g-node.org/ioannis.agtzidis/hollywood2_em.git`

at commit:

`870fa6d6209c9085260918d61433a0a2c70fd497`

The frozen author-statement record is also bound to:

- authoritative ground-truth evidence fingerprint `d5375b8768984ef76da02597c55b225aaff4088fd24698c0d53363e2df6b20ea`;
- underlying Hollywood-2 rights evidence fingerprint `6227045c3cc831b3669b34ca74b955847df4b26fafbf825c9a1b5473e25bc943`.

Frozen evidence record:

`validation/evidence/hollywood2/hollywood2-author-license-statement-evidence-v1.json`

Frozen evidence fingerprint:

`b01da719afe18f4eb0103a17d6e8c85f3750ba299050f8026063a9ebb55b1b2e`

## What remains unresolved

The dissertation statement does **not** identify the exact licence name, version, or complete licence text. No `LICENSE` or `COPYING` file has been recovered from the pinned GIN revision. Therefore GazeForge still records:

- exact GIN dataset licence: **unverified**;
- GIN analysis-use terms: **unresolved exact terms**;
- GIN raw-data redistribution terms: **unresolved exact terms**;
- participant identity mapping: **unverified**;
- source-audit readiness: **false**.

The article's CC BY 4.0 licence is not promoted to a dataset licence. The separate academic-use terms for the original Mathe–Sminchisescu Hollywood-2 gaze distribution are also not automatically inherited by the later Hollywood2EM annotation repository.

## Scientific boundary

This tranche creates **rights-context provenance only**. It does not authorize an empirical source audit and does not create participant-disjoint Hollywood2 validation, Lund↔Hollywood2 cross-dataset results, or a Frozen Evidence performance claim.

The next rights milestone remains recovery of an exact dataset-specific licence identifier/text or an equivalent author/institutional clarification that explicitly defines analysis and redistribution permissions for the Hollywood2EM GIN files.
