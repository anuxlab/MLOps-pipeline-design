# GitHub MLOps Laboratory

A reproducible, runner-based simulation of Machine Learning Operations (MLOps), designed to evolve into three independently executable pipelines:

- **CI** — continuous integration for code, data, features and models
- **CT** — continuous training with validation and retraining triggers
- **CD** — continuous delivery with model packaging, promotion and rollback simulation

This repository is currently at **Phase 1: Infrastructure and baseline**. It deliberately starts with a lightweight CPU-only scikit-learn workload so the pipeline can run on standard GitHub-hosted runners.

## Phase 1 capabilities

- Deterministic synthetic classification data generation
- Train/test split with a fixed random seed
- Logistic Regression baseline model
- Accuracy, precision, recall, F1 and ROC-AUC metrics
- Model artifact (`joblib`) and machine-readable metadata
- Execution profiling: wall time, process CPU time and peak RSS where supported
- A manually triggered GitHub Actions workflow
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
```

Outputs are written to `artifacts/runs/<run_id>/`:

```text
artifacts/runs/<run_id>/
├── model.joblib
├── metrics.json
├── run_metadata.json
└── resource_profile.json
```

The `run_id` is deterministic by default for a given invocation timestamp? No: a unique UTC timestamp plus short UUID is used to avoid overwriting prior runs. Model training itself is deterministic for the configured seed.

## Run options

```bash
python -m mlops_lab.cli run-baseline \
  --config configs/baseline.yaml \
  --output-dir artifacts/runs
```

## GitHub Actions

Go to **Actions → Phase 1 - Baseline ML → Run workflow**. The workflow is intentionally `workflow_dispatch` only; it does not run on every push.

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
| 1 | Repository foundation, baseline ML workload, runner profiling |
| 2 | CI: tests, data contracts, feature checks, model quality gates |
| 3 | CT: data versions, drift, scheduled/manual retraining |
| 4 | CD: model registry, staging, API tests, promotion and rollback |
| 5 | End-to-end orchestration and artifact handoffs |
| 6 | Monitoring, fault injection and recovery |
| 7 | Benchmark experiments and statistical analysis |
| 8 | Research documentation and reproducible results |

## Repository layout

See `docs/architecture.md` and `docs/phase1-implementation.md`.
