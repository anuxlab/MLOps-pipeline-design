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


## GitHub-hosted validation — 2026-11-06

Phase 4 passed on GitHub Actions run `42175951737`.

### Automatic source discovery

- Automatically selected Phase 3 run: `42175857188`.
- Candidate artifact: `phase3-candidate-42175857188-1`.
- Selection mode: `automatic`.
- Source branch: `main`.
- Source commit: `25bca6d6f4d00b558e55439845e79c44e9f07d3b`.
- Candidate artifact ID: `13482578103`.
- Artifact download and SHA-256 digest verification succeeded.

### Phase 3 candidate evidence

- Scenario: `covariate_shift`.
- CT status: `passed`.
- Drift detected in 10/20 features (50%).
- Retraining triggered because of feature drift.
- Candidate trained and promoted.
- Baseline accuracy: 0.7307.
- Candidate accuracy: 0.7653.
- Accuracy improvement: 0.0347 (3.47 percentage points).
- Candidate ROC-AUC: 0.8500.
- Candidate quality gates passed.

### CD result

- Delivery tests: 33 passed.
- Environment: `dev`.
- Registered model version: `v20261106T064109Z-fabb90fb`.
- Source CT run recorded in registry: `42175857188`.
- Number of input features: 20.
- Model SHA-256: `5ef0716ea4de7c1d477ac14dbdfd0aedd94cf0c443497aafce7ed3f69e0ff3ad`.
- Registry artifact ID: `13482543311`.
- Diagnostics artifact ID: `13482144347`.

The uploaded registry archive was inspected independently. It contains the `dev` environment pointer, the versioned model, the delivery manifest and the original CT model manifest. The manifest checksum matches the model artifact's checksum recorded by the CT pipeline.

**Conclusion:** Phase 4's automatic Phase 3 candidate discovery, cross-run artifact download, provenance validation, model registration and dev environment pointer update are GitHub-hosted validated. This is a simulated filesystem deployment, not an external production deployment.
