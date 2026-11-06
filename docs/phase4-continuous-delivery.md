# Phase 4 — Continuous Delivery (CD)

## Purpose
Consume a **promoted candidate produced by Phase 3**, verify its provenance and integrity, register an immutable model version, and update a simulated deployment environment. This phase does not retrain the model.

## Automatic Phase 3 candidate discovery

Automatic discovery is the default. The manually triggered Phase 4 workflow:

1. Queries the GitHub Actions API for completed, successful runs of `phase3-ct.yml` on the selected branch.
2. Inspects candidate artifacts belonging to each run, newest first.
3. Considers only the candidate artifact named `phase3-candidate-<run_id>-<run_attempt>` for the run's latest attempt. This avoids accidentally selecting a candidate from an earlier rerun attempt.
4. Skips stable runs (which publish diagnostics but no candidate), failed runs, wrong-branch runs and expired candidate artifacts.
5. Downloads the newest eligible candidate artifact using the workflow's `GITHUB_TOKEN`.
6. Fails with a diagnostic message if no eligible candidate exists in the configured discovery window.

The workflow requires `actions: read` and `contents: read` permissions. It uses the repository-provided `GITHUB_TOKEN`; no personal access token or additional secret is required for same-repository artifact discovery and download.

### Candidate artifact contract

Every CT execution publishes a diagnostic artifact named `phase3-ct-<run_id>-<run_attempt>`. Only a promoted candidate publishes a second artifact named `phase3-candidate-<run_id>-<run_attempt>`, containing exactly:

- `candidate_model.joblib`
- `ct_report.json`
- `model_manifest.json`

The model manifest records the source run ID, attempt, commit, branch, filenames, promotion status and SHA-256 checksum. Phase 4 requires the three files to be co-located and rejects missing/ambiguous triplets, failed or unpromoted reports, provenance mismatches, checksum mismatches and incompatible serialized models.

## Manual override

The Phase 4 workflow remains manually triggered. Leave `source_ct_run_id` and `source_artifact_name` blank to use automatic discovery. For reproducibility or debugging, provide **both** fields to select a specific candidate artifact. Supplying only one is rejected. `target_environment` defaults to `dev`; `discovery_limit` defaults to 20 recent workflow runs.

## Delivery controls

1. Verify CT report status and `candidate.trained == true` and `candidate.promoted == true`.
2. Verify the manifest's pipeline, promotion flag, source run identity and SHA-256 checksum.
3. Deserialize the estimator and verify its prediction interface.
4. Copy it into a versioned filesystem registry and preserve its source manifest.
5. Generate a delivery manifest with model version, source run, commit, metrics, feature count and SHA-256.
6. Update only the requested environment pointer (`dev`, `staging`, or `prod`).
7. Verify the checksum whenever the environment model is loaded.

Successful registry snapshots and failure diagnostics are uploaded separately. A failed registration cannot be mistaken for a successful registry export.

## Prediction API

`mlops_lab.service:app` exposes `/health` and `/predict`. Set `MLOPS_REGISTRY_DIR` and `MLOPS_ENVIRONMENT` before running Uvicorn:

```bash
MLOPS_REGISTRY_DIR=model_registry MLOPS_ENVIRONMENT=dev uvicorn mlops_lab.service:app --host 127.0.0.1 --port 8000
```

## GitHub procedure

1. Run Phase 3 with `covariate_shift` or `concept_drift` and confirm candidate promotion. Stable runs are valid CT outcomes but intentionally do not produce deployable candidate artifacts.
2. Open **Actions → Phase 4 - Continuous Delivery → Run workflow**.
3. Leave both source fields blank for automatic discovery, or provide both for a manual override.
4. Select the target environment and run the workflow.
5. Inspect the `phase4-registry-*` artifact after success. The `phase4-diagnostics-*` artifact is retained separately for troubleshooting.

## Important limitations

- GitHub-hosted runners are ephemeral. The registry uploaded as an Actions artifact is a reproducible delivery snapshot, not a durable production registry.
- This phase simulates deployment by updating an environment pointer. It does not deploy to a public endpoint.
- `prod` is an environment label in the simulation. Configure GitHub Environment required reviewers before treating it as an approval-controlled production deployment.
- Joblib model files are executable serialization formats. Only download and load artifacts produced by trusted workflows in this repository.


## Automatic Phase 3 candidate discovery (updated)

The Phase 4 workflow now discovers the newest eligible, unexpired `phase3-candidate-<run_id>-<attempt>` artifact from a successful Phase 3 run on the `main` branch. The diagnostic artifact `phase3-ct-*` is never accepted for deployment.

The two manual source inputs (`source_ct_run_id` and `source_artifact_name`) are optional. Leave both blank for automatic discovery. If either is supplied, both must be supplied and are checked against GitHub's run and artifact metadata before download.

The Phase 3 workflow must also be updated: it publishes `phase3-ct-*` diagnostics for every run and `phase3-candidate-*` only when a candidate is promoted. A stable run intentionally produces diagnostics only.

**Upgrade note:** replace both `.github/workflows/phase3-ct.yml` and `.github/workflows/phase4-cd.yml` from this repository version, commit and push them to `main`, then run Phase 3 with `covariate_shift` or `concept_drift` before running Phase 4.
