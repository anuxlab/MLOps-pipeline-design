# Phase 7 — Benchmarking and Experimental Evaluation

## Objective

Measure repeatable pipeline execution cost and robustness across CI, CT and monitoring scenarios on GitHub-hosted runners. The benchmark uses the Phase 5 registered model discovered automatically from the latest successful Phase 5 run on `main`.

## Experimental dimensions

- CI execution: repeated data/model quality-gate runs.
- CT execution: stable, covariate shift and concept drift.
- Monitoring: normal, prediction drift and quality degradation.
- Optional negative tests: corrupted CT input and invalid monitoring input.
- Repeats: 1, 2, 3 or 5 per workflow dispatch.

## Metrics

Each experiment records:
- wall-clock duration measured around the subprocess;
- child-process peak-RSS delta in platform resource units (Linux reports KiB);
- process return code and expected outcome;
- stdout/stderr tails for debugging;
- environment, Python version, run timestamp and scenario.

The output includes `benchmark_report.json` (full experiment records) and `benchmark_summary.csv` (analysis-friendly table). Negative tests are successful experiments when the expected failure is observed.

## Run

Open **Actions → Phase 7 - MLOps Benchmarking and Experiments → Run workflow**.

Recommended first run:
- Environment: `dev`
- Repeats: `1`
- Include negative tests: `true`

The workflow is manually triggered only. It downloads the Phase 5 registry artifact automatically; no run IDs or artifact names need to be entered.

## Interpretation and limitations

- Hosted-runner timings are noisy and should be summarized over repeated runs; do not treat one run as a stable performance estimate.
- `ru_maxrss` is a process high-water mark, not a precise per-step memory delta; the report labels its platform units explicitly.
- This first benchmark measures pipeline CLI workloads and monitoring scenarios, not full GitHub queue/setup/artifact transfer latency.
- Synthetic data makes experiments repeatable but does not establish production generalization.
- Compare medians and dispersion across repeated runs; record runner image, Python version and commit when reporting results.
