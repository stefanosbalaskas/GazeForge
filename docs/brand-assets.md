# Brand assets and sharing

GazeForge uses a compact geometric identity built around **gaze + auditability + analysis**. Branding is a presentation layer only: it does not change, summarize, or strengthen empirical evidence.

## Asset set

| Asset | Purpose |
| --- | --- |
| `assets/brand/gazeforge-mark.svg` | Primary compact mark for the documentation header and compact project surfaces |
| `assets/brand/gazeforge-favicon.svg` | Browser favicon; decorative version of the compact mark |
| `assets/brand/gazeforge-lockup.svg` | Horizontal wordmark and tagline for repository/documentation presentation |
| `assets/brand/gazeforge-social-preview.svg` | Editable vector source for the repository social preview |
| `assets/brand/gazeforge-social-preview.png` | 1280×640 upload-ready social preview |

The mark combines a gaze aperture, a sample point, and a review/check trace. It is intentionally geometric rather than anatomical: it should not be interpreted as surveillance, diagnosis, emotion detection, or eye-health inference.

## Scientific boundary

The identity does **not** imply benchmark validation, tracker-specific validity, or autonomous AI decision-making. In particular:

- derived 60 Hz evidence remains derived and is not native Gazepoint GP3 validation;
- synthetic/demo visuals remain software demonstrations rather than empirical evidence;
- unresolved benchmark identity, rights, task-mapping, or source gates remain unresolved;
- AI outputs remain reviewable data products and never silently replace the empirical record.

## Accessibility and motion

Informative vector assets carry a `<title>` and `<desc>`. Decorative favicon/hero use is deliberately hidden from assistive technology because the adjacent text already names the project. Critical meaning is carried by text as well as shape; it is not encoded by colour alone.

The website keeps non-essential hover motion behind `prefers-reduced-motion: no-preference` and disables it when reduced motion is requested.

## Repository social preview

The repository includes `assets/brand/gazeforge-social-preview.png` at **1280×640 px** with a solid background for reliable rendering across sharing clients.

The GitHub repository setting still requires a manual UI action because the current repository connector does not expose social-preview upload:

1. Open **Settings → General** for the GazeForge repository.
2. Find **Social preview**.
3. Upload `docs/assets/brand/gazeforge-social-preview.png`.
4. Save the repository setting.

Uploading that image changes presentation only; it does not alter documentation evidence or release state.
