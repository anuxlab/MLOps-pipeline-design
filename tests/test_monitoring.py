import json
import joblib
import numpy as np
from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from mlops_lab.monitoring import run_monitoring
from mlops_lab.registry import register_and_deploy, sha256


def make_registry(tmp_path):
    from sklearn.model_selection import train_test_split
    X_all, y_all = make_classification(
        n_samples=6000, n_features=20, n_informative=12, n_redundant=4,
        n_classes=2, class_sep=1.0, flip_y=0.02, random_state=42
    )
    _, X, _, y = train_test_split(
        X_all, y_all, test_size=0.5, random_state=43, stratify=y_all
    )
    X = X.copy()
    X[:, :10] += 1.5
    scaler = StandardScaler().fit(X)
    model = LogisticRegression(max_iter=1000).fit(scaler.transform(X), y)
    source = tmp_path / "candidate"
    source.mkdir()
    model_path = source / "candidate_model.joblib"
    joblib.dump({"model": model, "scaler": scaler}, model_path)
    (source / "ct_report.json").write_text(json.dumps({
        "status": "passed", "source": {"github_run_id": "test-run"},
        "candidate": {"trained": True, "promoted": True,
                      "metrics": {"accuracy": 0.8, "roc_auc": 0.85}}
    }))
    (source / "model_manifest.json").write_text(json.dumps({
        "schema_version": 1, "pipeline": "continuous_training",
        "candidate_promoted": True, "source_run_id": "test-run",
        "model_file": "candidate_model.joblib", "report_file": "ct_report.json",
        "checksum_algorithm": "sha256", "model_sha256": sha256(model_path)
    }))
    register_and_deploy(source, tmp_path / "registry", "dev")
    return tmp_path / "registry"

def test_normal_monitoring_writes_report(tmp_path):
    registry = make_registry(tmp_path)
    out = run_monitoring(registry, "dev", tmp_path / "monitor", "normal")
    report = json.loads((out / "monitoring_report.json").read_text())
    assert report["status"] == "passed"
    assert report["performance"]["n_samples"] == 1000
    assert report["monitoring_decision"] in {"healthy", "alert"}


def test_prediction_drift_generates_alert(tmp_path):
    registry = make_registry(tmp_path)
    out = run_monitoring(registry, "dev", tmp_path / "monitor", "prediction_drift")
    report = json.loads((out / "monitoring_report.json").read_text())
    assert report["data_drift"]["drifted_fraction"] >= 0.3
    assert any(a["type"] == "feature_drift" for a in report["alerts"])


def test_quality_degradation_generates_critical_alert(tmp_path):
    registry = make_registry(tmp_path)
    out = run_monitoring(registry, "dev", tmp_path / "monitor", "quality_degradation")
    report = json.loads((out / "monitoring_report.json").read_text())
    assert any(a["type"] == "performance_degradation" for a in report["alerts"])


def test_invalid_input_fails_but_preserves_report(tmp_path):
    registry = make_registry(tmp_path)
    try:
        run_monitoring(registry, "dev", tmp_path / "monitor", "invalid_input")
        assert False, "expected monitoring to reject invalid input"
    except RuntimeError as exc:
        assert "input contract" in str(exc)
    reports = list((tmp_path / "monitor").rglob("monitoring_report.json"))
    assert len(reports) == 1
    assert json.loads(reports[0].read_text())["status"] == "failed"
