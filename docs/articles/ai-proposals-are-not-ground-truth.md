---
tags:
  - Articles
  - AI
  - Validation
  - AOI
  - Events
---

# AI proposals are not ground truth

Computer vision and machine learning can reduce manual work in eye-tracking research. The scientific risk appears when a prediction is silently promoted into an empirical fact.

## Keep prediction identity

Preserve the model, version, parameters, confidence, input identity, preprocessing assumptions, and inference run identity when relevant.

## Separate proposal from review

An object detector may propose a box. A tracker may extend it through time. A classifier may propose an event label. These can be useful research artifacts without being treated as ground truth.

![Validation workflow from labels and grouping design to held-out predictions and bounded claims](../assets/figures/event-validation-workflow.svg)

## Validate at the level of the intended claim

If the intended use is participant-general event classification, participant-held-out evaluation matters. If the intended claim concerns native 60 Hz recordings, derived 60 Hz evidence cannot silently substitute for native acquisition.

## Dynamic AOIs need temporal support

Interpolation between reviewed keyframes is different from extrapolation outside reviewed support.

![Dynamic AOI support showing reviewed keyframes, bounded interpolation and prohibited extrapolation](../assets/figures/dynamic-aoi-support.svg)

## Continue

- [Event-model validation clinic](../event-model-validation-clinic.md)
- [Dynamic AOIs](../dynamic-aois.md)
- [Dynamic AOI evaluation](../dynamic-aoi-evaluation.md)
- [Validation evidence guide](../validation-evidence-guide.md)
