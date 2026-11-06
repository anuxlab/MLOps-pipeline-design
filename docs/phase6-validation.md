# Phase 6 — GitHub-hosted validation

## Run identity

- Workflow: Phase 6 - Model Monitoring and Reliability
- GitHub Actions run: `42178707720`
- Scenario: `normal`
- Environment: `dev`
- Monitoring artifact: `phase6-monitoring-42178707720-1`
- Artifact ID: `13484152722`

## Registry discovery and retrieval

- Selected Phase 5 run: `42176888963`.
- Selected registry artifact: `phase5-registry-42176888963-1`.
- Registry artifact ID: `13482679410`.
- Model version: `v20261106T065115Z-ab43dbfe`.
- Environment pointer: `dev`.
- Downloaded artifact digest verified by GitHub Actions.

## Monitoring results

- Status: `passed`.
- Decision: `healthy`.
- Samples: 1,000.
- Features: 20.
- Drifted features: 0 (0%).
- KS test: no feature crossed alpha 0.01.
- Prediction PSI: 0.007537.
- Accuracy: 0.773.
- ROC-AUC: 0.870251.
- Alerts: 0.
- Model SHA-256: `6c2b0e0b7bbbd7b28fa30662364c018f54da65b98e984445530aada10166d4db`.

The monitoring artifact contains `monitoring_report.json` and `monitoring_metadata.json`. The metadata report checksum matches the report bytes.

## Conclusion and scope

The normal Phase 6 hosted path is validated end to end: automatic Phase 5 registry discovery, cross-run artifact download, registry/model loading, monitoring and evidence upload all succeeded.

The `prediction_drift`, `quality_degradation` and `invalid_input` scenarios have not yet been validated on GitHub-hosted runners. The normal scenario alone does not establish those paths.
