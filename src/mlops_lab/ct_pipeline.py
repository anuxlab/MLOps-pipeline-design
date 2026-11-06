from datetime import datetime, timezone
from pathlib import Path
import json
import platform
import uuid

import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.datasets import make_classification

from .contracts import validate_dataset
from .data import generate_classification_data
from .drift import detect_feature_drift
from .evaluation import evaluate_classifier
from .features import transform_features
from .model import build_model
from .profiling import profile_execution


def _dump(path, payload):
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _make_reference_current(data_cfg, scenario):
    """Create disjoint reference/current windows from one common data-generating process."""
    n_samples = int(data_cfg["n_samples"])
    X_all, y_all = make_classification(
        n_samples=2 * n_samples,
        n_features=int(data_cfg["n_features"]),
        n_informative=int(data_cfg["n_informative"]),
        n_redundant=int(data_cfg["n_redundant"]),
        n_classes=int(data_cfg["n_classes"]),
        class_sep=float(data_cfg["class_sep"]),
        flip_y=float(data_cfg["flip_y"]),
        random_state=int(data_cfg.get("reference_seed", 42)),
    )
    X_reference, X_current, y_reference, y_current = train_test_split(
        X_all, y_all, test_size=0.5,
        random_state=int(data_cfg.get("current_seed", 43)),
        stratify=y_all,
    )

    if scenario == "covariate_shift":
        shift = float(data_cfg.get("covariate_shift", 1.5))
        X_current = X_current.copy()
        X_current[:, :max(1, X_current.shape[1] // 2)] += shift
    elif scenario == "concept_drift":
        # Features retain their distribution, while the target relationship changes.
        y_current = 1 - y_current
    elif scenario == "corrupted_data":
        X_current = X_current.copy()
        X_current[0, 0] = np.nan
    elif scenario != "stable":
        raise ValueError(f"Unsupported CT scenario: {scenario}")

    return X_reference, y_reference, X_current, y_current


def _fit_and_score(model_cfg, X_train, X_test, y_train, y_test):
    X_train_scaled, X_test_scaled, scaler = transform_features(X_train, X_test)
    model = build_model(model_cfg)
    model.fit(X_train_scaled, y_train)
    metrics = evaluate_classifier(model, X_test_scaled, y_test)
    return model, scaler, metrics


def run_ct(config: dict, output_dir=None, scenario="stable") -> Path:
    """Run continuous-training simulation with drift, validation and promotion gates."""
    data_cfg = config["data"]
    model_cfg = config["model"]
    ct_cfg = config.get("ct", {})
    exec_cfg = config.get("execution", {})
    base = Path(output_dir or exec_cfg.get("output_dir", "artifacts/ct-runs"))
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    run_dir = base / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    report = {
        "run_id": run_id,
        "pipeline": "CT",
        "scenario": scenario,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "status": "failed",
        "errors": [],
    }
    profile = {}

    try:
        with profile_execution() as profile:
            X_ref, y_ref, X_current, y_current = _make_reference_current(data_cfg, scenario)

            reference_validation = validate_dataset(
                X_ref, y_ref,
                min_samples=int(ct_cfg.get("min_samples", 100)),
                expected_features=int(data_cfg["n_features"]),
            )
            current_validation = validate_dataset(
                X_current, y_current,
                min_samples=int(ct_cfg.get("min_samples", 100)),
                expected_features=int(data_cfg["n_features"]),
            )
            report["data_validation"] = {
                "reference": reference_validation.to_dict(),
                "current": current_validation.to_dict(),
                "passed": reference_validation.passed and current_validation.passed,
            }
            if not reference_validation.passed or not current_validation.passed:
                raise ValueError("CT data validation failed; training was not started.")

            # Hold out a current-window evaluation set, keeping the same test set
            # for baseline and candidate comparisons.
            X_train, X_eval, y_train, y_eval = train_test_split(
                X_current, y_current,
                test_size=float(data_cfg.get("test_size", 0.25)),
                random_state=int(data_cfg.get("evaluation_seed", 2026)),
                stratify=y_current,
            )

            drift = detect_feature_drift(
                X_ref, X_current,
                alpha=float(ct_cfg.get("drift_alpha", 0.01)),
                min_drifted_fraction=float(ct_cfg.get("min_drifted_fraction", 0.30)),
            )
            report["drift"] = drift

            # Baseline is trained on the reference window and evaluated on current data.
            X_ref_train, X_ref_test, y_ref_train, y_ref_test = train_test_split(
                X_ref, y_ref,
                test_size=float(data_cfg.get("test_size", 0.25)),
                random_state=int(data_cfg.get("reference_eval_seed", 2025)),
                stratify=y_ref,
            )
            baseline_model, baseline_scaler, baseline_metrics = _fit_and_score(
                model_cfg, X_ref_train, X_eval, y_ref_train, y_eval
            )

            min_baseline = float(ct_cfg.get("minimum_baseline_accuracy", 0.70))
            performance_degraded = baseline_metrics["accuracy"] < min_baseline
            retraining_triggered = bool(drift["drift_detected"] or performance_degraded)
            report["baseline"] = {
                "metrics": baseline_metrics,
                "minimum_accuracy": min_baseline,
                "performance_degraded": performance_degraded,
            }
            report["trigger_decision"] = {
                "retraining_triggered": retraining_triggered,
                "reasons": [
                    reason for reason, active in [
                        ("feature_drift", drift["drift_detected"]),
                        ("baseline_performance_below_threshold", performance_degraded),
                    ] if active
                ],
            }

            if retraining_triggered:
                candidate_model, candidate_scaler, candidate_metrics = _fit_and_score(
                    model_cfg, X_train, X_eval, y_train, y_eval
                )
                improvement = float(candidate_metrics["accuracy"] - baseline_metrics["accuracy"])
                min_candidate = float(ct_cfg.get("minimum_candidate_accuracy", 0.70))
                min_improvement = float(ct_cfg.get("minimum_accuracy_improvement", 0.02))
                candidate_valid = candidate_metrics["accuracy"] >= min_candidate
                promoted = bool(candidate_valid and improvement >= min_improvement)
                report["candidate"] = {
                    "metrics": candidate_metrics,
                    "accuracy_improvement": improvement,
                    "minimum_accuracy": min_candidate,
                    "minimum_improvement": min_improvement,
                    "quality_gate_passed": candidate_valid,
                    "promoted": promoted,
                }
                if promoted:
                    joblib.dump(
                        {"model": candidate_model, "scaler": candidate_scaler},
                        run_dir / "candidate_model.joblib",
                    )
            else:
                report["candidate"] = {
                    "trained": False,
                    "promoted": False,
                    "reason": "No retraining trigger; retain current model.",
                }

        report["resource_profile"] = profile
        report["status"] = "passed"
        report["decision"] = (
            "candidate_promoted"
            if report["candidate"].get("promoted", False)
            else "retain_existing_model"
        )
    except Exception as exc:
        report["errors"].append(f"{type(exc).__name__}: {exc}")
        report["resource_profile"] = profile
        report["status"] = "failed"

    _dump(run_dir / "ct_report.json", report)
    _dump(run_dir / "resource_profile.json", profile)

    if report["status"] != "passed":
        raise RuntimeError(f"CT pipeline failed. Report: {run_dir / 'ct_report.json'}")
    return run_dir
