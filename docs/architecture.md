# Architecture

```text
raw/vendor data
      |
      v
canonical gaze schema
      |
      +----> QC anomaly scoring --------+
      |                                 |
      +----> event model probabilities -+--> reviewed/locked analytic table
      |                                 |
stimulus --> semantic AOI proposals ----+
                    |
                    v
               human review
                    |
                    v
            fixation-to-AOI map
                    |
                    v
             semantic scanpaths
                    |
                    +--> motifs
                    +--> learned embeddings
                    +--> clustering/similarity

Every major transformation can be fingerprinted and recorded in an AuditTrail.
```

Model-specific adapters are optional. Core analysis remains usable without a GPU or network.
