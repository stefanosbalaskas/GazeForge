# Hollywood2EM GIN host and registry metadata

GazeForge carries a reviewed, fail-closed rights-context record for the public
Hollywood2EM annotation repository. This tranche narrows the remaining licence
question without converting metadata observations into permission claims.

## Reviewed first-party host observation

Workflow `34058146019` ran on exact head
`7d0ba3fcb5a41c5771e7b64b4fcbf7aa5e27ee71` and reached both public GIN
surfaces successfully.

The GIN repository API returned HTTP `200` JSON for
`ioannis.agtzidis/hollywood2_em`. The reviewed response identifies repository
ID `834`, default branch `master`, and the description
`Hand labelled eye movements for a subset of the Hollywood2 data set`.
The recursive metadata review found **no key path containing `license` or
`licence`**.

The public repository page also returned HTTP `200`. In the reviewed response,
neither the `license` nor `licence` keyword occurred, while the repository slug
was present.

These are bounded observations of the reviewed public surfaces. They do **not**
establish that licence terms are absent globally, historically, in an
unreviewed host surface, or in author/institutional correspondence.

## DataCite cross-check

The same workflow queried DataCite using four bounded searches:

| Query | Reported | Returned | Exact Hollywood2EM repository-URL matches |
| --- | ---: | ---: | ---: |
| `hollywood2` | 27 | 27 | 0 |
| `hollywood2_em` | 0 | 0 | 0 |
| `ioannis.agtzidis` | 1 | 1 | 0 |
| exact repository fragment | 0 | 0 | 0 |

A zero exact match is **not** promoted to a global claim that no DOI,
registration, or licence exists.

## Immutable evidence

The reviewed accessible-host record is:

`validation/evidence/hollywood2/hollywood2-gin-host-metadata-accessible-evidence-v1.json`

Evidence fingerprint:

`9e09bfe43a273fbcd8cfe258be547aee18e96b8f0928198d1fb5411555024ced`

It is bound to:

- workflow `34058146019`;
- exact probe head `7d0ba3fcb5a41c5771e7b64b4fcbf7aa5e27ee71`;
- artifact `9996628764`;
- artifact ZIP SHA-256
  `ceb1da449b2407186ecfbae9eff09a3133050dc2b28f4330c54644fc8743a49d`;
- live-probe fingerprint
  `fd66a389c0bfd6b9e225524bd6847eecd5bf21fba56a46c0aa897dac54aeae27`;
- live-probe JSON SHA-256
  `70f89cbacb30e874973b7f3af2f9851fd72c2630f2737759f8367e2825b3ad6e`.

The record also binds the canonical GIN commit and the already-frozen
authoritative-ground-truth, annotation-provenance, complete-history,
underlying-rights, and author-license-statement evidence fingerprints.

## Rights boundary

The new observation improves the provenance record but does not resolve the
licence.

GazeForge still records:

- exact Hollywood2EM annotation licence identifier/text: **unrecovered**;
- analysis-use authorization from exact repository terms: **unresolved**;
- raw-annotation redistribution authorization: **unresolved**;
- global host-metadata licence absence: **not claimed**;
- author or host clarification for exact terms: **still required**.

The author's dissertation statement that the Chapter 4 data were publicly
available with an open-source licence remains relevant context, but it does not
supply an exact licence identifier or full permission scope. The original
Hollywood-2 academic-use terms remain a separate rights layer and are not
automatically inherited by the later GIN annotations.

## Scientific boundary

This tranche creates no new empirical result. It does not verify participant
identity mapping, create participant-disjoint validation, create
Lund↔Hollywood2 cross-dataset validation, establish independent human-human
agreement, authorize a source audit, or create a new performance Frozen
Evidence claim.

A future GIN response that exposes a licence field, repository-page licence
wording, or an exact DataCite repository match is deliberately treated as a
review event rather than being auto-promoted to authorization.
