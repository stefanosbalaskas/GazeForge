# Security policy

## Supported versions

GazeForge is currently alpha research software. Security fixes are applied to the latest code on
`main` until the first stable release establishes a formal support window.

## Reporting a vulnerability

Please use GitHub's private security-advisory mechanism for the repository when available rather
than opening a public issue containing exploit details, credentials, tokens, or sensitive data.

Do not attach participant-level research data to a security report. A minimal synthetic reproducer
is preferred whenever possible.

## Model and data safety

Model files and benchmark artifacts should be treated as untrusted inputs unless their provenance
and fingerprints are known. GazeForge does not require cloud upload of participant data for its
core functionality; local processing is the preferred default for sensitive research workflows.
