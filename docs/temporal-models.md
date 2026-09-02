# Temporal-context event models

The first GazeForge temporal model is a deliberately modest **context MLP**. It gives the event
classifier access to neighbouring gaze samples while keeping the implementation within the core
scientific Python dependency stack.

`train_context_event_classifier()` constructs a symmetric window around every sample, using
kinematic and missingness features. Windows are built independently inside each participant/trial
group, so context never crosses a trial boundary.

The window is specified in milliseconds and converted to samples using the recording rate. For
example, a 50 ms radius at 60 Hz becomes three samples on either side of the centre sample.

`ai_classify_events_context()` returns per-class probabilities, confidence, model/version metadata,
and the effective temporal radius. It applies the same sampling-rate compatibility guardrail as the
non-temporal event model.

Temporal windows are constructed positionally, so duplicate or non-unique input DataFrame indices
do not alter row alignment. The returned classification table preserves the original input index.

This model is a **temporal baseline**, not a performance claim. It must be compared with I-VT and
the Random Forest baseline under participant-held-out and dataset-held-out validation before any
claim that temporal context improves event detection. CNN and transformer models remain later
candidates under identical frozen benchmark splits.
