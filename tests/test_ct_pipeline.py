import json
import pytest
from mlops_lab.config import load_config
from mlops_lab.ct_pipeline import run_ct


def test_stable_ct_retains_existing_model(tmp_path):
    config = load_config("configs/ct.yaml")
    run_dir = run_ct(config, tmp_path, scenario="stable")
    report = json.loads((run_dir / "ct_report.json").read_text())
    assert report["status"] == "passed"
    assert report["trigger_decision"]["retraining_triggered"] is False
    assert report["decision"] == "retain_existing_model"
    assert not (run_dir / "candidate_model.joblib").exists()


def test_concept_drift_triggers_candidate_training(tmp_path):
    config = load_config("configs/ct.yaml")
    run_dir = run_ct(config, tmp_path, scenario="concept_drift")
    report = json.loads((run_dir / "ct_report.json").read_text())
    assert report["status"] == "passed"
    assert report["trigger_decision"]["retraining_triggered"] is True
    assert "baseline_performance_below_threshold" in report["trigger_decision"]["reasons"]
    assert report["candidate"]["promoted"] is True
    assert (run_dir / "candidate_model.joblib").exists()
    manifest = json.loads((run_dir / "model_manifest.json").read_text())
    assert manifest["candidate_promoted"] is True
    assert manifest["model_sha256"]


def test_corrupted_data_fails_validation_and_keeps_report(tmp_path):
    config = load_config("configs/ct.yaml")
    with pytest.raises(RuntimeError, match="CT pipeline failed"):
        run_ct(config, tmp_path, scenario="corrupted_data")
    run_dirs = list(tmp_path.iterdir())
    report = json.loads((run_dirs[0] / "ct_report.json").read_text())
    assert report["status"] == "failed"
    assert report["data_validation"]["current"]["passed"] is False


def test_covariate_shift_triggers_and_promotes_candidate(tmp_path):
    config = load_config("configs/ct.yaml")
    run_dir = run_ct(config, tmp_path, scenario="covariate_shift")
    report = json.loads((run_dir / "ct_report.json").read_text())
    assert report["status"] == "passed"
    assert report["drift"]["drift_detected"] is True
    assert "feature_drift" in report["trigger_decision"]["reasons"]
    assert report["candidate"]["promoted"] is True
    assert (run_dir / "candidate_model.joblib").exists()
