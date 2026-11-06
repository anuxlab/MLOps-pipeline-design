"""Discover the newest successful Phase 3 run with an unexpired candidate artifact."""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API_VERSION = "2022-11-28"


class GitHubAPI:
    def __init__(self, repository: str, token: str):
        self.repository = repository
        self.token = token

    def get(self, path: str):
        url = f"https://api.github.com/repos/{self.repository}/{path}"
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": API_VERSION,
                "User-Agent": "mlops-laboratory-candidate-discovery",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))


def discover_latest_candidate(api: GitHubAPI, branch: str, limit: int = 20):
    query = urllib.parse.urlencode(
        {"status": "completed", "per_page": min(max(limit, 1), 100), "branch": branch}
    )
    runs_payload = api.get(f"actions/workflows/phase3-ct.yml/runs?{query}")
    runs = runs_payload.get("workflow_runs", [])
    examined = 0
    for run in runs:
        if run.get("status") != "completed" or run.get("conclusion") != "success":
            continue
        if run.get("head_branch") != branch:
            continue
        examined += 1
        run_id = str(run.get("id"))
        run_attempt = str(run.get("run_attempt", "1"))
        artifacts_payload = api.get(f"actions/runs/{run_id}/artifacts?per_page=100")
        # A rerun can leave artifacts from an earlier attempt attached to the same run.
        # Only consider the artifact emitted by the run's latest attempt.
        expected_name = f"phase3-candidate-{run_id}-{run_attempt}"
        candidates = [
            artifact for artifact in artifacts_payload.get("artifacts", [])
            if artifact.get("name") == expected_name
            and not artifact.get("expired", False)
        ]
        if candidates:
            # Attempt-specific name; newest is the latest upload for this run.
            candidates.sort(key=lambda item: item.get("created_at", ""), reverse=True)
            return {
                "run_id": run_id,
                "artifact_name": candidates[0]["name"],
                "head_sha": run.get("head_sha"),
                "head_branch": run.get("head_branch"),
                "run_url": run.get("html_url"),
                "examined_runs": examined,
            }
    raise RuntimeError(
        f"No unexpired promoted Phase 3 candidate artifact found on branch '{branch}'. "
        f"Inspected {examined} successful completed run(s) (limit {limit}). "
        "Run Phase 3 with covariate_shift or concept_drift and ensure the candidate passes its gates."
    )



def validate_manual_candidate(api: GitHubAPI, run_id: str, artifact_name: str, branch: str):
    """Validate manual overrides against the Phase 3 run and its current artifact."""
    run = api.get(f"actions/runs/{run_id}")
    if run.get("status") != "completed" or run.get("conclusion") != "success":
        raise RuntimeError(f"Selected Phase 3 run {run_id} is not successfully completed.")
    if run.get("head_branch") != branch:
        raise RuntimeError(
            f"Selected Phase 3 run belongs to branch '{run.get('head_branch')}', "
            f"not requested branch '{branch}'."
        )
    attempt = str(run.get("run_attempt", "1"))
    expected_name = f"phase3-candidate-{run_id}-{attempt}"
    if artifact_name != expected_name:
        raise RuntimeError(
            f"'{artifact_name}' is not the expected deployable candidate artifact "
            f"for run {run_id}, attempt {attempt}. Expected '{expected_name}'. "
            "The phase3-ct-* artifact is diagnostic-only."
        )
    payload = api.get(f"actions/runs/{run_id}/artifacts?per_page=100")
    matches = [
        item for item in payload.get("artifacts", [])
        if item.get("name") == artifact_name and not item.get("expired", False)
    ]
    if not matches:
        raise RuntimeError(
            f"Deployable candidate artifact '{artifact_name}' is missing or expired "
            f"for Phase 3 run {run_id}."
        )
    return {
        "run_id": str(run_id),
        "artifact_name": artifact_name,
        "head_sha": run.get("head_sha"),
        "head_branch": run.get("head_branch"),
        "run_url": run.get("html_url"),
        "selection": "manual",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manual-run-id", default="")
    parser.add_argument("--manual-artifact-name", default="")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    if bool(args.manual_run_id) != bool(args.manual_artifact_name):
        raise SystemExit("Manual source requires both source run ID and artifact name.")

    repository = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    branch = os.environ.get("SOURCE_BRANCH") or os.environ.get("GITHUB_REF_NAME", "")
    if not repository or not token or not branch:
        raise SystemExit("GITHUB_REPOSITORY, GITHUB_TOKEN and source branch are required.")
    api = GitHubAPI(repository, token)
    if args.manual_run_id:
        selected = validate_manual_candidate(
            api, args.manual_run_id, args.manual_artifact_name, branch
        )
    else:
        selected = discover_latest_candidate(api, branch, args.limit)
        selected["selection"] = "automatic"

    print(json.dumps(selected, indent=2))
    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as output:
            for key in ("run_id", "artifact_name", "selection"):
                output.write(f"{key}={selected[key]}\n")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"GitHub API error {exc.code}: {detail}", file=sys.stderr)
        raise
