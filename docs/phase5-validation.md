# Phase 5 — GitHub-hosted validation

## Run identity

- GitHub Actions run: `42176888963`
- Branch: `main`
- Commit: `a0b45fd5a18e4737e3fa9aad0a59dcb199469bfa`
- Scenario: `covariate_shift`
- Target environment: `dev`
- CI, CT, candidate and registry artifacts were supplied and independently inspected.

## CI artifact

- Status: passed.
- Accuracy: 0.7776.
- Precision: 0.7729.
- Recall: 0.7853.
- F1: 0.7790.
- ROC-AUC: 0.8617.
- Data contract and feature transformation checks passed.
- Accuracy and ROC-AUC gates passed.

## CT artifact

- Status: passed.
- Drift method: two-sample Kolmogorov–Smirnov.
- Drifted features: 10 / 20 (50%).
- Retraining triggered due to feature drift.
- Baseline accuracy: 0.7307.
- Candidate accuracy: 0.7653.
- Accuracy improvement: 0.0347.
- Candidate quality gate and promotion passed.

## Candidate and registry artifacts

- Candidate files: `candidate_model.joblib`, `ct_report.json`, `model_manifest.json`.
- Source run ID: `42176888963`; attempt: `1`.
- Registry version: `v20261106T065115Z-ab43dbfe`.
- Environment pointer: `dev`.
- Registry manifest source run ID matches candidate provenance.
- Candidate and registry model SHA-256 both equal:
  `6c2b0e0b7bbbd7b28fa30662364c018f54da65b98e984445530aada10166d4db`.
- Registry archive contains model, version manifest, source manifest and environment pointer.

## Conclusion

Phase 5 CI → CT → CD orchestration is validated from the supplied GitHub-hosted artifacts. All four archives passed ZIP integrity checks. The artifact handoff, promotion decision, registry pointer and model checksum are consistent.
