from pathlib import Path
import pytest
from mlops_lab.config import load_config
from mlops_lab.ci_pipeline import run_ci


CONFIG = Path(__file__).parents[1] / "configs" / "baseline.yaml"


def test_ci_pipeline_passes_and_writes_report(tmp_path):
    config = load_config(CONFIG)
    config["ci"] = {"min_samples": 100, "quality_gates": {"accuracy": 0.70, "roc_auc": 0.75}}
    run_dir = run_ci(config, tmp_path)
    report = __import__("json").loads((run_dir / "ci_report.json").read_text())
    assert report["status"] == "passed"
    assert report["checks"]["data_contract"]["passed"]
    assert (run_dir / "candidate_model.joblib").exists()


@pytest.mark.parametrize("failure_mode", ["invalid_schema", "nan_feature", "force_quality_gate"])
def test_ci_failure_modes_write_reports(tmp_path, failure_mode):
    config = load_config(CONFIG)
    config["ci"] = {"min_samples": 100, "quality_gates": {"accuracy": 0.70, "roc_auc": 0.75}}
    with pytest.raises(RuntimeError, match="CI pipeline failed"):
        run_ci(config, tmp_path, failure_mode=failure_mode)
    reports = list(tmp_path.rglob("ci_report.json"))
    assert reports
    report = __import__("json").loads(reports[-1].read_text())
    assert report["status"] == "failed"
