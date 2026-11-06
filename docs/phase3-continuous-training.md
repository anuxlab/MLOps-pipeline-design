# Phase 3 — Continuous Training (CT)

## Goal

Simulate a continuous-training lifecycle on ephemeral GitHub Actions runners. The pipeline compares a reference data window with a current data window, validates both, detects feature distribution drift, evaluates the existing baseline model on current labeled data, and conditionally trains a candidate model.

## Scenarios

| Scenario | Change | Expected behavior |
|---|---|---|
| `stable` | Same generating distribution | No retraining trigger; retain current model |
| `covariate_shift` | Shift selected feature distributions | Feature drift signal; train candidate |
| `concept_drift` | Change feature/target relationship by inverting current labels | Baseline quality degradation; train candidate |
| `corrupted_data` | Inject a NaN into current features | Fail data validation; do not train |

## Detection methods

### Feature drift

Each feature is compared using the two-sample Kolmogorov–Smirnov test. A feature is flagged when its p-value is below `drift_alpha`. Aggregate drift is flagged when the fraction of flagged features reaches `min_drifted_fraction`.

This is a univariate distribution-shift screen. It does not detect all multivariate shifts and is not, by itself, proof of concept drift. Multiple testing and sample-size effects should be considered in research interpretation.

### Performance degradation

A baseline model trained on the reference window is evaluated on a held-out current-window evaluation set. Retraining is triggered if baseline accuracy falls below the configured minimum.

### Candidate gate

A candidate is trained on the current training partition and evaluated on the same current evaluation partition. Promotion is simulated only if:
- candidate accuracy meets the configured minimum; and
- candidate accuracy improves over the baseline by at least the configured margin.

A candidate artifact is saved only when the promotion gate passes. This is a simulation of promotion eligibility, not a persistent production registry update.

## CLI

```bash
python -m mlops_lab.cli run-ct --config configs/ct.yaml --scenario stable
python -m mlops_lab.cli run-ct --config configs/ct.yaml --scenario covariate_shift
python -m mlops_lab.cli run-ct --config configs/ct.yaml --scenario concept_drift
python -m mlops_lab.cli run-ct --config configs/ct.yaml --scenario corrupted_data
```

The corrupted-data scenario is expected to exit non-zero while preserving `ct_report.json`.

## Outputs

- `ct_report.json`: validations, drift statistics, trigger decision, baseline/candidate metrics and promotion decision
- `resource_profile.json`: wall time, process CPU time and RSS observations
- `candidate_model.joblib`: emitted only when candidate promotion gates pass

## Limitations

- Synthetic scenarios are controlled simulations, not evidence of performance on a real production stream.
- The KS test compares each feature independently and does not model feature dependencies.
- Concept drift is demonstrated through a deliberately changed label relationship.
- Current labels are assumed available for evaluation. Real production systems may have delayed or partial labels.
- A passing candidate is not automatically deployed; CD is implemented in Phase 4.
- Each GitHub-hosted job is ephemeral. Later orchestration must transfer outputs using workflow artifacts or another explicit storage layer.
