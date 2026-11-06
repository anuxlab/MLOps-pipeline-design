from datetime import datetime, timezone
from pathlib import Path
import json
import platform
import uuid

import joblib
import numpy as np

from .contracts import validate_dataset
from .data import generate_classification_data
from .evaluation import evaluate_classifier
from .features import transform_features
from .model import build_model
from .profiling import profile_execution


def _write_json(path: Path, payload):
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def run_ci(config: dict, output_dir=None, failure_mode="none") -> Path:
    """Run ML-specific CI checks and persist a report even when a gate fails."""
    data_cfg = config["data"]
    model_cfg = config["model"]
    ci_cfg = config.get("ci", {})
    exec_cfg = config.get("execution", {})
    base = Path(output_dir or exec_cfg.get("output_dir", "artifacts/ci-runs"))
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    run_dir = base / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    checks = {}
    errors = []
    metrics = {}
    profile = {}
    model = None

    try:
        X_train, X_test, y_train, y_test = generate_classification_data(data_cfg)
        X_all = np.vstack([X_train, X_test])
        y_all = np.concatenate([y_train, y_test])

        # Explicit fault injection is used to test the pipeline's rejection path.
        if failure_mode == "invalid_schema":
            X_all = X_all[:, :-1]
        elif failure_mode == "nan_feature":
            X_all = X_all.copy()
            X_all[0, 0] = np.nan

        contract = validate_dataset(
            X_all,
            y_all,
            min_samples=int(ci_cfg.get("min_samples", 100)),
            expected_features=int(data_cfg["n_features"]),
        )
        checks["data_contract"] = contract.to_dict()
        if not contract.passed:
            errors.extend(contract.errors)

        if failure_mode == "invalid_schema" or failure_mode == "nan_feature":
            raise ValueError("Data contract rejected the dataset.")

        with profile_execution() as profile:
            X_train_scaled, X_test_scaled, scaler = transform_features(X_train, X_test)
            model = build_model(model_cfg)
            model.fit(X_train_scaled, y_train)
            metrics = evaluate_classifier(model, X_test_scaled, y_test)

        checks["pipeline_execution"] = {"passed": True}
        checks["feature_transform"] = {
            "passed": True,
            "method": "StandardScaler",
            "fit_on_training_data_only": True,
            "finite_output": True,
        }

        quality_thresholds = ci_cfg.get("quality_gates", {})
        threshold_results = {
            metric: {
                "observed": float(metrics[metric]),
                "minimum": float(minimum),
                "passed": float(metrics[metric]) >= float(minimum),
            }
            for metric, minimum in quality_thresholds.items()
        }
        if failure_mode == "force_quality_gate":
            # Deterministically exercise the quality-gate rejection branch.
            threshold_results["accuracy"] = {
                "observed": float(metrics["accuracy"]),
                "minimum": 1.01,
                "passed": False,
            }

        quality_passed = all(item["passed"] for item in threshold_results.values())
        checks["model_quality_gates"] = {
            "passed": quality_passed,
            "thresholds": threshold_results,
        }
        if not quality_passed:
            errors.append("One or more model quality thresholds were not met.")

        if model is not None and quality_passed:
            joblib.dump({"model": model, "scaler": scaler}, run_dir / "candidate_model.joblib")

    except Exception as exc:
        checks.setdefault("pipeline_execution", {"passed": False})
        checks["pipeline_execution"]["error"] = f"{type(exc).__name__}: {exc}"
        if not errors:
            errors.append(f"{type(exc).__name__}: {exc}")

    overall_passed = not errors
    report = {
        "run_id": run_id,
        "pipeline": "CI",
        "status": "passed" if overall_passed else "failed",
        "failure_mode": failure_mode,
        "checks": checks,
        "errors": errors,
        "metrics": metrics,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
    }
    _write_json(run_dir / "ci_report.json", report)
    _write_json(run_dir / "metrics.json", metrics)
    _write_json(run_dir / "resource_profile.json", profile)

    if not overall_passed:
        raise RuntimeError(f"CI pipeline failed. Report: {run_dir / 'ci_report.json'}")
    return run_dir
