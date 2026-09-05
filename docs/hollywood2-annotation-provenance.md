# Hollywood2EM annotation provenance

GazeForge now freezes a third Hollywood2 provenance layer: **author-level licensing
declaration evidence for the later Hollywood2EM annotation distribution**, together with
upstream participant-ID context from the original Hollywood-2 data source.

This layer is deliberately separate from both the original Mathe–Sminchisescu gaze-data
licence and the exact GIN repository-byte audit.

## Author-level open-source declaration

Ioannis Agtzidis's 2020 TUM dissertation, *Towards a better understanding of eye movements in
natural contexts*, introduces Chapter 4, *Hand-labeled data sets*, with the statement:

> “All the data presented in this chapter are made publicly available with an open-source
> license.”

Footnote 2 on that statement points directly to:

```text
https://gin.g-node.org/ioannis.agtzidis/hollywood2_em
```

The dissertation was submitted to the Technical University of Munich on 15 June 2020 and
accepted on 8 September 2020. This is materially stronger than inferring rights from the
Hollywood2EM article licence or from the licence of the older underlying gaze distribution:
it is a dataset-author declaration that explicitly binds the chapter's Hollywood2EM data to
the GIN repository.

The frozen evidence record is:

```text
validation/evidence/hollywood2/hollywood2-annotation-provenance-evidence-v1.json
```

with fingerprint:

```text
a08510e43caca2a8e6d5c85e7b1ad41c9f312247cd9bd8367372f8ecad8aacab
```

## What the declaration does not prove

The dissertation does **not** name an exact licence identifier in the declaration, reproduce
the licence text, or provide a repository `LICENSE`/`COPYING` file. GazeForge therefore keeps:

- `analysis_use_terms_status=unresolved`;
- `raw_data_redistribution_terms_status=unresolved`;
- `dataset_specific_license_verified=false`;
- `license_inference_permitted=false`.

The phrase “open-source license” is evidence that an author intended the Hollywood2EM data to
be openly licensed; it is **not** substituted for exact legal terms. The article's CC BY 4.0
licence is still not treated as a dataset licence, and the original Hollywood-2 academic-use
licence is still not inherited by the later GIN annotation repository.

## Upstream subject-ID context

Stefan Mathe's 2015 dissertation, *Actions in the Eye*, provides a separate participant
provenance fact for the original public Hollywood-2 eye-movement data: it states that the
public dataset lists unique subject identifiers within each task group. The same chapter
reports 12 Hollywood-2 action-recognition participants and 4 free-viewing participants.

The audited GIN annotation tree exposes 16 recurring filename tokens:

```text
001 002 003 004 005 006 008 010 011 012 013 014 015 017 018 019
```

The matching count and the upstream unique-ID statement strengthen the case that the tokens
are participant-like identifiers. They still do **not** establish an authoritative linkage
between each GIN prefix and the original subject IDs or task groups. GazeForge therefore
continues to record:

- `participant_identity_mapping_verified=false`;
- `participant_group_membership_by_gin_token_verified=false`;
- `mapping_inference_permitted=false`.

Participant-disjoint modelling remains blocked.

## Scientific boundary

This tranche verifies two previously missing provenance statements without crossing their
evidential limits:

1. the Hollywood2EM dataset author explicitly described the chapter data, including
   Hollywood2EM via footnote 2, as publicly available under an open-source licence;
2. the original Hollywood-2 public dataset used unique subject IDs within groups.

It does **not** create an exact annotation-repository licence, redistribution permission,
GIN-token-to-participant mapping, independent human-human agreement, participant-held-out
model result, Lund↔Hollywood2 result, or canonical Frozen Evidence performance claim.

## Next required evidence

The remaining high-leverage Hollywood2 gates are now narrower:

1. recover exact Hollywood2EM licence text or an author/institutional statement naming the
   licence and redistribution scope;
2. recover an authoritative statement or archive structure that links the GIN filename
   prefixes to original subject IDs and task groups;
3. only after item 2, execute participant-disjoint Hollywood2 model validation;
4. only after the same provenance boundary is satisfied, execute Lund↔Hollywood2
   cross-dataset validation.
