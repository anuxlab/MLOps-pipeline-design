# Phase 1 — GitHub-hosted runner validation record

## Evidence source

The repository owner supplied the GitHub Actions log export for workflow run `42162795127`, job `Test and train baseline`, executed on 6 November 2026.

## Observed results

| Check | Observed result |
|---|---:|
| Runner Python | 3.11.18 |
| Logical CPU count reported | 4 |
| Unit tests | 4 passed in 1.11 s |
| Accuracy | 0.7776 |
| Precision | 0.7728707 |
| Recall | 0.7852564 |
| F1 | 0.7790143 |
| ROC-AUC | 0.8618006 |
| Profiled training wall time | 0.015854 s |
| Process CPU time | 0.045366 s |
| Peak RSS | 180,400,128 bytes |
| Artifact upload | Successful; 2,041 bytes |

## Conclusion

The supplied log confirms that dependency installation, editable package installation, all four Phase 1 unit tests, baseline model training, metric generation, resource profiling and artifact upload completed successfully on a GitHub-hosted Ubuntu runner.

The `wall_time_seconds` field measures the code region wrapped by the profiler, not the complete workflow or job duration. End-to-end workflow duration must be measured separately from GitHub Actions job timestamps.

## Follow-up

Phase 2 adds ML-specific data contracts, leakage-safe feature scaling, model quality gates and controlled failure injection. Its tests are locally validated; the new Phase 2 workflow still needs to be pushed and executed in the target GitHub repository.
