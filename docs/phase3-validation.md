# Phase 3 — Local validation record

Date: 2026-11-06

## Automated tests

- Full test suite: **17 passed**
- Runtime: 1.76 seconds
- Environment: local Linux container, Python 3.13.5

## Controlled scenario checks

| Scenario | Pipeline status | Drift fraction | Baseline accuracy | Candidate accuracy | Decision |
|---|---|---:|---:|---:|---|
| stable | passed | 0.00 | 0.7613 | Not trained | Retain existing model |
| covariate_shift | passed | 0.50 | 0.7307 | 0.7653 | Candidate promoted |
| concept_drift | passed | 0.00 | 0.2173 | 0.7827 | Candidate promoted |
| corrupted_data | failed as expected | Not calculated | Not calculated | Not trained | Reject invalid data |

The corrupted-data scenario intentionally exits non-zero after persisting its CT report. The other three scenarios complete successfully.

## Important validation boundary

These results are local functional validation. The Phase 3 GitHub Actions workflow has not yet been run on a hosted runner. The first GitHub run should use `stable`, followed by `covariate_shift`, `concept_drift`, and `corrupted_data`. The last scenario is expected to show a failed workflow while uploading its diagnostic report.

## Interpretation

- Stable data does not cause an unnecessary retraining run.
- Covariate shift triggers retraining through the KS-based feature drift signal.
- Concept drift is demonstrated by changing the label relationship while keeping feature distributions unchanged; baseline performance drops and candidate retraining recovers performance.
- Corrupted data is rejected before model training.
- Candidate promotion is simulated through quality and minimum-improvement gates. It does not deploy the candidate; deployment belongs to Phase 4.


## GitHub Actions shell continuation fix (November 2026)

A GitHub-hosted run exposed a workflow YAML shell issue: the `run-ct` command had
literal doubled backslashes at line endings. Bash passed a literal `\\` to the
CLI, so argparse rejected it and subsequent option lines were treated as
commands. The Phase 3 workflow now invokes the CLI on one physical shell line,
avoiding continuation escaping entirely:

```bash
python -m mlops_lab.cli run-ct --config configs/ct.yaml --output-dir artifacts/ct-runs --scenario "$CT_SCENARIO"
```

The workflow still captures the CT exit code, discovers and uploads the generated
report for diagnostics, and uploads a deployable candidate only when the CT
report confirms promotion. The four scenarios were locally re-executed:
`stable`, `covariate_shift`, and `concept_drift` passed; `corrupted_data` failed
as designed after writing its diagnostic report.
