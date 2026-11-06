import pytest
from mlops_lab.candidate_discovery import discover_latest_candidate, validate_manual_candidate


class FakeAPI:
    def __init__(self, runs, artifacts):
        self.runs = runs
        self.artifacts = artifacts
        self.calls = []

    def get(self, path):
        self.calls.append(path)
        if path.startswith("actions/workflows/"):
            return {"workflow_runs": self.runs}
        parts = path.split("/")
        run_id = parts[2]
        if "/artifacts" in path:
            return {"artifacts": self.artifacts.get(run_id, [])}
        return next(item for item in self.runs if str(item["id"]) == str(run_id))


def run(run_id, branch="main", conclusion="success"):
    return {"id": run_id, "status": "completed", "conclusion": conclusion,
            "head_branch": branch, "head_sha": f"sha-{run_id}", "run_attempt": 1,
            "html_url": f"https://github.com/example/repo/actions/runs/{run_id}"}


def artifact(name, expired=False):
    return {"name": name, "expired": expired, "created_at": "2026-11-06T05:00:00Z"}


def test_discovers_latest_successful_run_with_candidate_artifact():
    api = FakeAPI(
        [run(300), run(200), run(100, conclusion="failure")],
        {"300": [artifact("phase3-ct-300-1")],
         "200": [artifact("phase3-candidate-200-1")]},
    )
    selected = discover_latest_candidate(api, "main", 20)
    assert selected["run_id"] == "200"
    assert selected["artifact_name"] == "phase3-candidate-200-1"


def test_skips_expired_candidate_and_wrong_branch():
    api = FakeAPI(
        [run(300, branch="feature"), run(200)],
        {"200": [artifact("phase3-candidate-200-1", expired=True)]},
    )
    with pytest.raises(RuntimeError, match="No unexpired promoted"):
        discover_latest_candidate(api, "main", 20)


def test_ignores_stable_run_without_candidate_artifact():
    api = FakeAPI([run(300), run(200)], {"300": [], "200": [artifact("phase3-candidate-200-1")]})
    selected = discover_latest_candidate(api, "main", 20)
    assert selected["run_id"] == "200"


def test_does_not_select_candidate_from_earlier_rerun_attempt():
    latest_attempt = run(400)
    latest_attempt["run_attempt"] = 2
    api = FakeAPI(
        [latest_attempt],
        {"400": [artifact("phase3-candidate-400-1")]},
    )
    with pytest.raises(RuntimeError, match="No unexpired promoted"):
        discover_latest_candidate(api, "main", 20)


def test_manual_candidate_requires_deployable_candidate_artifact():
    api = FakeAPI(
        [run(500)],
        {"500": [artifact("phase3-candidate-500-1")]},
    )
    selected = validate_manual_candidate(api, "500", "phase3-candidate-500-1", "main")
    assert selected["run_id"] == "500"
    assert selected["selection"] == "manual"


def test_manual_candidate_rejects_diagnostic_artifact():
    api = FakeAPI([run(500)], {"500": [artifact("phase3-ct-500-1")]})
    with pytest.raises(RuntimeError, match="diagnostic-only"):
        validate_manual_candidate(api, "500", "phase3-ct-500-1", "main")


def test_manual_candidate_rejects_missing_or_expired_artifact():
    api = FakeAPI([run(500)], {"500": [artifact("phase3-candidate-500-1", expired=True)]})
    with pytest.raises(RuntimeError, match="missing or expired"):
        validate_manual_candidate(api, "500", "phase3-candidate-500-1", "main")


def test_manual_candidate_rejects_wrong_branch():
    api = FakeAPI([run(500, branch="feature")], {"500": [artifact("phase3-candidate-500-1")]})
    with pytest.raises(RuntimeError, match="belongs to branch"):
        validate_manual_candidate(api, "500", "phase3-candidate-500-1", "main")
