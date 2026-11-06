# Phase 1 — Implementation and validation

## Objective

Create a small, deterministic ML workload that can be executed locally and on a GitHub-hosted CPU runner. It establishes the conventions for configuration, CLI execution, model artifacts, metrics and resource profiles.

## Workload

- Task: binary classification
- Data: synthetic data generated with scikit-learn
- Estimator: Logistic Regression
- Split: stratified train/test split
- Random seed: 42 by default

## Outputs

| File | Purpose |
|---|---|
| `model.joblib` | Serialized trained estimator |
| `metrics.json` | Classification quality metrics |
| `run_metadata.json` | Run identity, data dimensions and versions |
| `resource_profile.json` | Wall time, CPU time and memory observations |

## Validation criteria

1. The data generator is deterministic for a fixed seed.
2. The training code produces a loadable model.
3. The evaluation report contains accuracy, precision, recall, F1 and ROC-AUC.
4. Unit tests pass before training runs in CI.
5. Workflow outputs are uploaded even though the hosted runner is ephemeral.

## Interpretation cautions

- A single run is a functional smoke test, not a statistically meaningful benchmark.
- Peak RSS is process-level maximum resident set size and may include interpreter/library allocations.
- GitHub-hosted runner CPU and memory characteristics can vary; benchmark conclusions require repeated runs and runner metadata.
- The artifact retention period is governed by the workflow's `retention-days` setting and repository/plan limits.
