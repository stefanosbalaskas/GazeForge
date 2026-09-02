# Dynamic semantic AOIs

Dynamic AOIs represent semantic regions whose geometry changes over time, such as objects in video,
scrolling interfaces, animated recommendations, or moving labels.

`DynamicAOIKeyframe` stores a stable AOI identity, semantic label, timestamp, rectangular geometry,
confidence, source, and optional model/version metadata. A track is the ordered set of keyframes
sharing one `aoi_id`.

`interpolate_dynamic_aoi()` performs linear interpolation only when the requested timestamp is
bracketed by two observed keyframes and the keyframe interval does not exceed `max_gap_ms`. It
never extrapolates before the first or after the last observed keyframe. This prevents an object
track from silently persisting after evidence for its location has ended.

`map_fixations_to_dynamic_aois()` evaluates each timestamped fixation against the geometry valid at
that instant. It preserves the selected AOI identity, label, confidence, source, model name/version,
and effective geometry timestamp. Overlap resolution is explicit (`highest_confidence`,
`smallest_area`, or `first`).

Detector/tracker backends implement the `DynamicAOIProvider` protocol. The core package therefore
does not bind dynamic AOIs to one computer-vision library. `CallableDynamicAOIProvider` can wrap a
research team's local detector/tracker while retaining the same downstream mapping API.

Dynamic AOIs remain proposals until validated. Empirical work should report frame-level detection
and tracking error, fixation-assignment agreement with expert AOIs, temporal-gap sensitivity, and
failure cases such as occlusion, scrolling discontinuities, and object re-identification errors.
