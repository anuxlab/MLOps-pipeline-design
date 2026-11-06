# Phase 2 — ML Continuous Integration

## Goal

Extend ordinary software CI with machine-learning-specific checks so that invalid data, broken feature transformations and underperforming candidate models are rejected before delivery.

## Pipeline stages

1. Load versioned YAML configuration.
2. Generate the deterministic synthetic classification workload.
3. Validate the data contract: matrix/target dimensions, row alignment, minimum sample count, expected feature count, finite values and at least two target classes.
4. Fit `StandardScaler` on the training partition only; transform train and test partitions.
5. Train the configured Logistic Regression estimator.
6. Evaluate accuracy, precision, recall, F1 and ROC-AUC.
7. Apply configurable model quality thresholds.
8. Serialize a candidate model together with its fitted scaler when checks pass.
9. Write `ci_report.json`, metrics and resource profile.
10. Return a non-zero process exit on a failed gate.

## Controlled failure modes

| Mode | Injected condition | Expected result |
|---|---|---|
| `none` | No fault | CI passes |
| `invalid_schema` | Remove a feature column | Data contract rejects |
| `nan_feature` | Inject NaN into feature matrix | Data contract rejects |
| `force_quality_gate` | Set accuracy threshold to 1.01 | Model quality gate rejects |

These modes are test fixtures, not production data mutation functionality.

## Report schema

`ci_report.json` contains run identity, pipeline status, failure mode, named checks, errors, evaluation metrics, timestamp and Python version. The report is written before the CLI raises on a failed run, so the GitHub workflow can upload diagnostics using an `if: always()` artifact step.

## Quality thresholds

The initial thresholds are configurable in `configs/ci.yaml`:

- Accuracy >= 0.70
- ROC-AUC >= 0.75

They are demonstration gates, not universal model acceptance criteria. A real project must derive thresholds from business requirements, class imbalance, baseline performance and validation methodology.

## Scope and limitations

- Data is synthetic and deterministic.
- The data contract currently validates array-level properties, not a production feature store schema.
- The model quality gate uses one fixed train/test split; later benchmarking should use repeated seeds or cross-validation.
- Feature scaling is fit only on training data to prevent test leakage.
- A passing CI candidate is not automatically deployed. CD will own promotion and release.
- Workflow is manually executable and reusable through `workflow_call`; no push-triggered execution is enabled.
