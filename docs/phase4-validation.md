# Phase 4 local validation record

- Date: 2026-11-06
- Python runtime: 3.13.5 (local sandbox)
- Automated suite: **22 passed**
- Workflow YAML: all four phase workflows parsed successfully
- Registry checks: promoted-candidate enforcement, immutable version folder, manifest generation, SHA-256 verification, tamper rejection, nested downloaded-artifact discovery
- API checks: FastAPI health and prediction endpoints tested with an isolated registry fixture
- End-to-end local CD smoke test: successfully registered an actual Phase 3 candidate from `artifacts/ct-validation/20261106T044423Z-f0617185` into the `dev` environment registry
- Actual candidate test metrics in its CT report: accuracy 0.7827, ROC-AUC 0.8580
- Feature count recorded in manifest: 20
- Model artifact integrity: SHA-256 recorded and verified on registry load

## GitHub validation status

Phase 4 has **not yet been executed on GitHub Actions**. The local test suite and local candidate handoff pass. The next validation is a manual Phase 4 workflow run using a Phase 3 run that produced a promoted candidate. A Phase 3 `stable` run is not a valid CD source because it intentionally has no candidate artifact.
