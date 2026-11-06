# Phase 5 Validation

## Local validation — 2026-11-06

- Existing automated test suite: 33 passed.
- Phase 2 CI CLI: passed.
- Phase 3 CT CLI (`covariate_shift`): passed.
- Candidate promotion: passed.
- Candidate manifest source run ID: `555555555` (local test fixture).
- Phase 4 registry CLI: passed.
- Target environment: `dev`.
- Registry environment pointer: created.
- Registry manifest records the source run ID and SHA-256 checksum.

The local simulation used the existing CI, CT and CD command-line interfaces sequentially. It validates the application-level pipeline contract, not GitHub Actions scheduling, artifact service behavior or hosted-runner permissions.

## GitHub validation pending

The Phase 5 workflow has not yet been executed on GitHub Actions. The first hosted run should use:

- Scenario: `covariate_shift`.
- Target environment: `dev`.
- Failure mode: `none`.

Expected jobs:

1. CI completes successfully and uploads `phase5-ci-*`.
2. CT detects drift, promotes a candidate, and uploads `phase5-ct-*` and `phase5-candidate-*`.
3. CD downloads the candidate from the same workflow run, validates it, registers it and uploads `phase5-registry-*`.

The `stable` scenario should complete CI and CT successfully while intentionally skipping CD because no candidate is promoted. `corrupted_data` should fail CT and must not run CD.
