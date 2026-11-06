"""Phase 6: model, data and prediction monitoring simulation."""
from __future__ import annotations

import hashlib
import json
import platform
import uuid
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from scipy.stats import ks_2samp
from sklearn.datasets import make_classification
from sklearn.metrics import accuracy_score, roc_auc_score

from .registry import load_environment_model, sha256


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _psi(reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    """Population Stability Index using reference quantile bins."""
    edges = np.unique(np.quantile(reference, np.linspace(0, 1, bins + 1)))
    if len(edges) < 3:
        return 0.0
    edges[0], edges[-1] = -np.inf, np.inf
    ref_counts = np.histogram(reference, bins=edges)[0].astype(float)
    cur_counts = np.histogram(current, bins=edges)[0].astype(float)
    ref_pct = np.clip(ref_counts / max(ref_counts.sum(), 1), 1e-6, None)
    cur_pct = np.clip(cur_counts / max(cur_counts.sum(), 1), 1e-6, None)
    return float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))


def run_monitoring(
    registry_dir: str | Path,
    environment: str = "dev",
    output_dir: str | Path = "artifacts/monitoring-runs",
    scenario: str = "normal",
    config_path: str | Path = "configs/monitoring.yaml",
) -> Path:
    if scenario not in {"normal", "prediction_drift", "quality_degradation", "invalid_input"}:
        raise ValueError(f"Unsupported monitoring scenario: {scenario}")
    cfg = json.loads(Path(config_path).read_text()) if str(config_path).endswith(".json") else None
    if cfg is None:
        import yaml
        cfg = yaml.safe_load(Path(config_path).read_text())
    artifact, manifest = load_environment_model(registry_dir, environment)
    model = artifact["model"] if isinstance(artifact, dict) else artifact
    scaler = artifact.get("scaler") if isinstance(artifact, dict) else None

    n = int(cfg.get("n_samples", 1000))
    n_features = int(manifest.get("n_features", 20))
    # Recreate the serving/reference distribution used by Phase 3's CT generator.
    # This avoids comparing unrelated synthetic datasets and producing false alerts.
    ct_cfg_path = Path(cfg.get("ct_config", "configs/ct.yaml"))
    if not ct_cfg_path.is_absolute():
        ct_cfg_path = Path.cwd() / ct_cfg_path
    import yaml
    ct_cfg = yaml.safe_load(ct_cfg_path.read_text())
    data_cfg = ct_cfg["data"]
    from sklearn.model_selection import train_test_split
    X_all, y_all = make_classification(
        n_samples=2 * int(data_cfg["n_samples"]),
        n_features=int(data_cfg["n_features"]),
        n_informative=int(data_cfg["n_informative"]),
        n_redundant=int(data_cfg["n_redundant"]),
        n_classes=int(data_cfg["n_classes"]),
        class_sep=float(data_cfg["class_sep"]),
        flip_y=float(data_cfg["flip_y"]),
        random_state=int(data_cfg.get("reference_seed", 42)),
    )
    _, X_ref, _, y_ref = train_test_split(
        X_all, y_all, test_size=0.5,
        random_state=int(data_cfg.get("current_seed", 43)),
        stratify=y_all,
    )
    X_ref = X_ref.copy()
    X_ref[:, : max(1, n_features // 2)] += float(data_cfg.get("covariate_shift", 1.5))
    # A fresh monitoring window from the same serving population.
    rng = np.random.default_rng(int(cfg.get("seed", 73)))
    row_indices = rng.integers(0, len(X_ref), size=n)
    X_cur = X_ref[row_indices].copy()
    y_cur = y_ref[row_indices].copy()
    X_ref = X_ref[:n].copy()
    y_ref = y_ref[:n].copy()
    if scenario == "prediction_drift":
        X_cur[:, : max(1, n_features // 2)] += float(cfg.get("shift", 1.5))
    elif scenario == "quality_degradation":
        y_cur = 1 - y_cur
    elif scenario == "invalid_input":
        X_cur[0, 0] = np.nan

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    out = Path(output_dir) / run_id
    out.mkdir(parents=True, exist_ok=False)
    report = {
        "schema_version": 1, "pipeline": "MONITORING", "run_id": run_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": environment, "model_name": manifest["model_name"],
        "model_version": manifest["version"], "model_sha256": manifest["model_sha256"],
        "scenario": scenario, "status": "failed", "alerts": [], "errors": [],
        "runtime": {"python_version": platform.python_version()},
    }
    try:
        if X_cur.ndim != 2 or X_cur.shape[1] != n_features or not np.isfinite(X_cur).all():
            raise ValueError("Current feature batch violates the model input contract.")
        ks_results = []
        for j in range(n_features):
            result = ks_2samp(X_ref[:, j], X_cur[:, j])
            ks_results.append({
                "feature_index": j, "statistic": float(result.statistic),
                "p_value": float(result.pvalue),
                "drift_detected": bool(result.pvalue < float(cfg.get("ks_alpha", 0.01))),
            })
        drifted = sum(x["drift_detected"] for x in ks_results)
        feature_fraction = drifted / n_features
        psi_values = []
        ref_input = scaler.transform(X_ref) if scaler is not None else X_ref
        cur_input = scaler.transform(X_cur) if scaler is not None else X_cur
        ref_pred = model.predict_proba(ref_input)[:, 1]
        cur_pred = model.predict_proba(cur_input)[:, 1]
        pred_psi = _psi(ref_pred, cur_pred)
        y_pred = model.predict(cur_input)
        accuracy = float(accuracy_score(y_cur, y_pred))
        try:
            auc = float(roc_auc_score(y_cur, cur_pred))
        except ValueError:
            auc = None
        thresholds = cfg.get("thresholds", {})
        if feature_fraction >= float(thresholds.get("drifted_feature_fraction", 0.3)):
            report["alerts"].append({"severity": "warning", "type": "feature_drift", "value": feature_fraction})
        if pred_psi >= float(thresholds.get("prediction_psi", 0.2)):
            report["alerts"].append({"severity": "warning", "type": "prediction_drift", "value": pred_psi})
        if accuracy < float(thresholds.get("minimum_accuracy", 0.65)):
            report["alerts"].append({"severity": "critical", "type": "performance_degradation", "value": accuracy})
        report.update({
            "status": "passed",
            "data_drift": {"method": "two_sample_kolmogorov_smirnov", "drifted_features": drifted,
                           "n_features": n_features, "drifted_fraction": feature_fraction,
                           "features": ks_results},
            "prediction_drift": {"method": "population_stability_index", "psi": pred_psi},
            "performance": {"accuracy": accuracy, "roc_auc": auc, "n_samples": n},
            "alert_count": len(report["alerts"]),
            "monitoring_decision": "alert" if report["alerts"] else "healthy",
        })
    except Exception as exc:
        report["errors"].append(str(exc))
        report["monitoring_decision"] = "invalid_or_unavailable"
    _write(out / "monitoring_report.json", report)
    _write(out / "monitoring_metadata.json", {
        "model_version": manifest["version"], "model_sha256": manifest["model_sha256"],
        "environment": environment, "scenario": scenario,
        "report_sha256": hashlib.sha256((out / "monitoring_report.json").read_bytes()).hexdigest(),
    })
    if report["status"] != "passed":
        raise RuntimeError(f"Monitoring failed: {report['errors']}")
    return out
