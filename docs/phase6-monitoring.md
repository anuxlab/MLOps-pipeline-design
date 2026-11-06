# Phase 6 — Model Monitoring and Reliability

## Objective

Monitor the model registered by Phase 5 without manually copying registry artifacts or run IDs. The Phase 6 workflow discovers the latest successful Phase 5 run on `main` that published a non-expired `phase5-registry-*` artifact, downloads it, and monitors the selected environment.

## Signals

1. **Feature/data drift:** per-feature two-sample Kolmogorov–Smirnov tests; report drifted-feature fraction.
2. **Prediction drift:** Population Stability Index (PSI) between reference and current model-score distributions.
3. **Model performance:** accuracy and ROC-AUC on a labeled monitoring simulation batch.
4. **Input contract:** dimensionality, feature count and finite-value validation.
5. **Model integrity:** registry model checksum verified by `load_environment_model` before inference.

The reference serving distribution is reconstructed using the same synthetic data-generation and covariate-shift parameters as Phase 3. This prevents unrelated synthetic datasets from generating false positive alerts in the healthy scenario.

## Alert thresholds

Configured in `configs/monitoring.yaml`:

- Feature drift: at least 30% of features significant at KS alpha 0.01.
- Prediction drift: PSI >= 0.20.
- Performance degradation: accuracy < 0.65.

Warnings and critical alerts are written to `monitoring_report.json`. Alerting is simulated through machine-readable reports; no external notification service is configured.

## Scenarios

| Scenario | Expected behavior |
|---|---|
| `normal` | Healthy, no alerts |
| `prediction_drift` | Feature and/or prediction drift warning |
| `quality_degradation` | Critical performance alert |
| `invalid_input` | Reject batch, preserve failed report, exit non-zero |

## Run locally

First obtain a Phase 5 registry artifact and extract it to `model_registry/`.

```bash
python -m mlops_lab.cli run-monitor --registry-dir model_registry --environment dev --output-dir artifacts/monitoring-runs --scenario normal
```

Other scenarios can be selected with `--scenario prediction_drift`, `quality_degradation`, or `invalid_input`.

## GitHub Actions

Run **Actions → Phase 6 - Model Monitoring and Reliability → Run workflow**. The workflow is manually triggered only. It automatically discovers the latest eligible Phase 5 registry artifact on `main`; no run ID or artifact name is required.

The workflow uploads monitoring reports even when input validation fails.

## Current limitations

This is a controlled monitoring simulation using generated labeled batches. It does not yet consume production telemetry, real-time feature stores, online prediction logs or ground-truth labels arriving asynchronously. Alert delivery is artifact/report based rather than PagerDuty, Slack or email. Thresholds are fixed configuration values and are not yet calibrated from historical production baselines.
