# Phase 4 — Continuous Delivery (CD)

## Purpose
Consume a **promoted candidate produced by Phase 3**, verify it, register an immutable version, and update a simulated deployment environment. This phase does not retrain the model.

## Artifact handoff
The manually triggered workflow downloads an artifact from a completed Phase 3 GitHub Actions run. Supply both the source run ID and the exact artifact name shown on that run. The downloaded artifact must contain `candidate_model.joblib` and `ct_report.json`. Stable CT runs intentionally have no candidate and are rejected.

## Delivery controls
1. Verify source report and `candidate.promoted == true`.
2. Deserialize the estimator and verify its prediction interface.
3. Copy it into a versioned filesystem registry.
4. Generate a manifest with model version, source run, metrics, feature count and SHA-256.
5. Update only the requested environment pointer (`dev`, `staging`, or `prod`).
6. Verify the checksum whenever the environment model is loaded.

The registry is a simulation artifact stored in the GitHub Actions artifact; it is not a durable production registry. Production deployment should replace this adapter with a managed registry/object store and an authenticated deployment target. Production approvals should be configured using GitHub Environments protection rules.

## Prediction API
`mlops_lab.service:app` exposes `/health` and `/predict`. Set `MLOPS_REGISTRY_DIR` and `MLOPS_ENVIRONMENT` before running Uvicorn:
```bash
MLOPS_REGISTRY_DIR=model_registry MLOPS_ENVIRONMENT=dev uvicorn mlops_lab.service:app --host 127.0.0.1 --port 8000
```

## Manual GitHub procedure
1. Run Phase 3 with `covariate_shift` or `concept_drift` and confirm it completes with `candidate.promoted: true`.
2. Open that Phase 3 run and copy its numeric run ID and exact artifact name.
3. Run **Phase 4 - Continuous Delivery** manually.
4. Provide the source run ID, exact artifact name, and target environment.
5. Download and inspect the resulting `phase4-cd-*` artifact. It contains the versioned model, manifest and environment pointer.

## Important limitations
- GitHub-hosted runners are ephemeral. A registry uploaded as an Actions artifact is a reproducible delivery snapshot, not a live durable registry.
- This phase simulates deployment by updating an environment pointer. It does not deploy to a public endpoint.
- `prod` is an environment label in the simulation. Configure GitHub Environment required reviewers before treating it as an approval-controlled production deployment.
