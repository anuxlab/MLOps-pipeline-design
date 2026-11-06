# GitHub MLOps Laboratory

A reproducible, runner-based simulation of Machine Learning Operations (MLOps), designed to evolve into three independently executable pipelines:

- **CI** — continuous integration for code, data, features and models
- **CT** — continuous training with validation and retraining triggers
- **CD** — continuous delivery with model packaging, promotion and rollback simulation

This repository currently includes **Phase 1: Infrastructure and baseline** and **Phase 2: ML Continuous Integration**. It deliberately starts with a lightweight CPU-only scikit-learn workload so the pipeline can run on standard GitHub-hosted runners.

## Current capabilities

- Deterministic synthetic classification data generation
- Train/test split with a fixed random seed
- Logistic Regression baseline model
- Accuracy, precision, recall, F1 and ROC-AUC metrics
- Model artifact (`joblib`) and machine-readable metadata
- Execution profiling: wall time, process CPU time and peak RSS where supported
- Manually triggered GitHub Actions workflows for baseline and ML CI
- Data contracts, train-only feature scaling, model quality gates and controlled failure injection
- Unit tests for data generation, training and metrics

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
python -m mlops_lab.cli run-baseline --config configs/baseline.yaml
pytest -q

# Phase 2 ML CI pipeline
python -m mlops_lab.cli run-ci --config configs/ci.yaml
```

Phase 1 outputs are written to `artifacts/runs/<run_id>/`; Phase 2 outputs are written to `artifacts/ci-runs/<run_id>/`.

```text
artifacts/
├── runs/<run_id>/                 # Phase 1
│   ├── model.joblib
│   ├── metrics.json
│   ├── run_metadata.json
│   └── resource_profile.json
└── ci-runs/<run_id>/              # Phase 2
    ├── candidate_model.joblib     # only when all gates pass
    ├── ci_report.json
    ├── metrics.json
    └── resource_profile.json
```

The `run_id` is deterministic by default for a given invocation timestamp? No: a unique UTC timestamp plus short UUID is used to avoid overwriting prior runs. Model training itself is deterministic for the configured seed.

## Run options

```bash
python -m mlops_lab.cli run-baseline \
  --config configs/baseline.yaml \
  --output-dir artifacts/runs
```

## Phase 2 — ML Continuous Integration

Run locally:

```bash
python -m mlops_lab.cli run-ci --config configs/ci.yaml
```

Exercise controlled rejection paths:

```bash
python -m mlops_lab.cli run-ci --config configs/ci.yaml --failure-mode invalid_schema
python -m mlops_lab.cli run-ci --config configs/ci.yaml --failure-mode nan_feature
python -m mlops_lab.cli run-ci --config configs/ci.yaml --failure-mode force_quality_gate
```

Each controlled failure should exit non-zero but still write `ci_report.json`, allowing the workflow to upload diagnostic evidence.

GitHub: **Actions → Phase 2 - ML Continuous Integration → Run workflow**. Select `none` for the normal passing run or a failure mode to test rejection behavior.

## GitHub Actions

Go to **Actions → Phase 1 - Baseline ML → Run workflow**. Both workflows are manually triggerable. Phase 2 is also reusable through `workflow_call`; neither runs automatically on every push.

The workflow:
1. Checks out the repository.
2. Sets up Python.
3. Installs dependencies.
4. Runs tests.
5. Executes the baseline training workload.
6. Uploads the run directory as a workflow artifact.

## Design decisions

- **No cloud credentials are required.**
- **No GPU or external dataset download is required.**
- Artifacts are passed between jobs/workflows using GitHub Actions artifacts in later phases.
- GitHub Actions artifacts are execution outputs, not a permanent model registry. A later phase will add explicit retention/versioning semantics.
- The runner profile is an observational estimate, not a complete hardware benchmark. Hosted runner hardware can vary.

## Roadmap

| Phase | Scope |
|---|---|
| 1 | Repository foundation, baseline ML workload, runner profiling | Completed |
| 2 | CI: tests, data contracts, feature checks, model quality gates | Implemented |
| 3 | CT: data versions, drift, scheduled/manual retraining |
| 4 | CD: model registry, staging, API tests, promotion and rollback |
| 5 | End-to-end orchestration and artifact handoffs |
| 6 | Monitoring, fault injection and recovery |
| 7 | Benchmark experiments and statistical analysis |
| 8 | Research documentation and reproducible results |

## Repository layout

See `docs/architecture.md`, `docs/phase1-implementation.md` and `docs/phase2-ci.md`.


## Phase 3: Continuous Training

The CT pipeline is independently executable through `.github/workflows/phase3-ct.yml`.

```bash
python -m mlops_lab.cli run-ct --config configs/ct.yaml --scenario stable
python -m mlops_lab.cli run-ct --config configs/ct.yaml --scenario covariate_shift
python -m mlops_lab.cli run-ct --config configs/ct.yaml --scenario concept_drift
python -m mlops_lab.cli run-ct --config configs/ct.yaml --scenario corrupted_data
```

Scenarios are controlled simulations:
- `stable`: no expected retraining trigger.
- `covariate_shift`: shift feature distributions and test drift-triggered retraining.
- `concept_drift`: change the current label relationship and test performance-triggered retraining.
- `corrupted_data`: inject a NaN and verify data validation prevents training.

CT reports contain data validation, KS drift statistics, baseline/candidate metrics, trigger reasons, promotion decision and resource profile. A candidate model is emitted only if its quality and improvement gates pass. Phase 4 will implement delivery/promotion orchestration.


## Phase 4 — Continuous Delivery
Phase 4 downloads a promoted candidate from a Phase 3 run, verifies and registers it with a SHA-256 manifest, and updates a simulated `dev`, `staging`, or `prod` environment pointer. It also includes a FastAPI prediction service.

See `docs/phase4-continuous-delivery.md`. The workflow is manually triggered only. It requires the Phase 3 run ID and exact artifact name; a stable run without a candidate is intentionally rejected.


### Phase 4 candidate discovery

Phase 4 now discovers the newest eligible promoted candidate from successful Phase 3 workflow runs on the selected branch. Leave `source_ct_run_id` and `source_artifact_name` blank in the Phase 4 dispatch form to use automatic discovery. Both inputs remain available as optional manual overrides and must be supplied together. Phase 3 publishes a separate `phase3-candidate-*` artifact only when the candidate passes promotion gates; stable runs publish diagnostics only.


### Phase 4 automatic candidate discovery

Phase 4 defaults to automatic discovery of the newest promoted Phase 3 candidate on `main`. The optional `source_ct_run_id` and `source_artifact_name` inputs should normally be left blank. Both must be supplied together when using a manual override.

Update and push **both** `.github/workflows/phase3-ct.yml` and `.github/workflows/phase4-cd.yml` from this repository before testing. Phase 3 uploads `phase3-candidate-<run_id>-<attempt>` only after promotion; `phase3-ct-*` is diagnostic-only. Run Phase 3 with `covariate_shift` or `concept_drift` to generate a deployable candidate.


## Phase 5: Integrated CI → CT → CD orchestration

Phase 5 provides one manually triggered workflow that executes the three MLOps stages in dependency order:

```text
CI (tests + quality gates) → CT (drift + conditional retraining) → CD (registry + environment pointer)
```

Run it from **Actions → Phase 5 - Integrated MLOps Orchestration → Run workflow**. The default `covariate_shift` scenario is designed to produce a promoted candidate and exercise the complete handoff. Select `stable` to validate the intentional no-candidate path, or `concept_drift` to exercise performance-triggered retraining. `corrupted_data` is an expected CT rejection test.

The pipeline uploads separate CI, CT, candidate and registry artifacts. CD downloads the candidate from the CT job in the same workflow run, so no run ID or artifact name needs to be entered manually. See `docs/phase5-orchestration.md`.


### Phase 5 validation status

The Phase 5 workflow is implemented and locally validated. Its GitHub-hosted run is pending. The standalone Phase 2, Phase 3 and Phase 4 workflows remain available for isolated validation.
