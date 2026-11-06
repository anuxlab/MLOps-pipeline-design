#!/usr/bin/env python3
"""Find the newest successful Phase 5 run that published a registry artifact."""
import json
import os
import sys
import urllib.error
import urllib.request


def api_get(url, token):
    request = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {token}",
                      "Accept": "application/vnd.github+json",
                      "X-GitHub-Api-Version": "2022-11-28"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GITHUB_TOKEN"]
    branch = os.environ.get("SOURCE_BRANCH", "main")
    base = f"https://api.github.com/repos/{repo}/actions"
    workflows = api_get(f"{base}/workflows?per_page=100", token)["workflows"]
    workflow = next((w for w in workflows if w["path"].endswith("/phase5-orchestration.yml")), None)
    if not workflow:
        raise RuntimeError("Could not find phase5-orchestration.yml in this repository.")
    runs = api_get(
        f"{base}/workflows/{workflow['id']}/runs?branch={branch}&status=completed&per_page=50",
        token
    )["workflow_runs"]
    for run in runs:
        if run.get("conclusion") != "success":
            continue
        run_id = str(run["id"])
        artifacts = api_get(f"{base}/runs/{run_id}/artifacts?per_page=100", token)["artifacts"]
        expected = f"phase5-registry-{run_id}-{run.get('run_attempt', 1)}"
        found = next((a for a in artifacts if a["name"] == expected and not a.get("expired")), None)
        if found:
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
                output.write(f"run_id={run_id}\n")
                output.write(f"artifact_name={expected}\n")
                output.write(f"run_url={run.get('html_url','')}\n")
            print(f"Selected Phase 5 run {run_id}, artifact {expected}")
            return
    raise RuntimeError(
        f"No successful Phase 5 run on branch '{branch}' with a non-expired registry artifact was found."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Registry discovery failed: {exc}", file=sys.stderr)
        raise
