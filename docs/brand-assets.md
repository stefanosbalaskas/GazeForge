# Brand assets and sharing

GazeForge is part of the shared **Python Suite research packages** family. Repository and documentation surfaces therefore use the **official Python Suite logo** as the primary package-family identity, while the GazeForge name and scientific scope remain explicit in text.

Branding is a presentation layer only. It does not summarize, strengthen, or replace the package's scientific evidence.

## Primary asset

| Asset | Purpose |
| --- | --- |
| `assets/python-suite-logo.png` | Official Python Suite shared package identity for the repository README, documentation header, favicon, and homepage |

The file is copied into this repository from the same canonical asset used by the other Python package site rather than hot-linked at runtime. Keeping a local copy makes the documentation build self-contained and prevents branding from changing if another repository is reorganized.

## GazeForge within Python Suite

The shared identity tells users that GazeForge belongs to the same research-software family as the other Python packages. The product-specific name remains **GazeForge**, and the site continues to describe its scope as auditable eye-tracking analysis: import, QC, review, events, AOIs, scanpaths, validation, provenance, and reporting.

The previous GazeForge-specific mark is no longer the primary website or repository logo. Historical vector/social-preview files may remain in the source tree for archival continuity, but user-facing package identity should use the official Python Suite asset.

## Scientific boundary

The Python Suite identity does **not** imply benchmark validation, tracker-specific validity, or autonomous AI decision-making. In particular:

- derived 60 Hz evidence remains derived and is not native Gazepoint GP3 validation;
- synthetic/demo visuals remain software demonstrations rather than empirical evidence;
- unresolved benchmark identity, rights, task-mapping, or source gates remain unresolved;
- AI outputs remain reviewable data products and never silently replace the empirical record.

## Accessibility and motion

The official logo is accompanied by text naming both **Python Suite** and **GazeForge**, so scientific meaning does not depend on interpreting the image. Interactive website components retain visible `:focus-visible` treatment, adequate target height, sticky-header scroll clearance, and a reduced-motion path.

Automated checks protect those implementation invariants, but they are not proof of complete WCAG conformance or complete usability. Manual keyboard, screen-reader, zoom, contrast, and mobile review remain separate activities.

## Sharing

When sharing the repository or documentation, prefer the package name plus the official family identity:

> **GazeForge — a Python Suite research package for auditable eye-tracking analysis.**

Use the exact release/version and evidence-status pages when the context is scientific rather than promotional.
