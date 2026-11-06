from datetime import datetime, timezone
from pathlib import Path
import json
import platform
import uuid

import joblib
import numpy as np

from .data import generate_classification_data
from .evaluation import evaluate_classifier
from .model import build_model
from .profiling import profile_execution


def _json_dump(path: Path, payload: dict):
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def run_baseline(config: dict, output_dir: str | Path | None = None) -> Path:
    data_cfg = config["data"]
    model_cfg = config["model"]
    execution_cfg = config.get("execution", {})
    base_output = Path(output_dir or execution_cfg.get("output_dir", "artifacts/runs"))
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    run_dir = base_output / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    with profile_execution() as profile:
        X_train, X_test, y_train, y_test = generate_classification_data(data_cfg)
        model = build_model(model_cfg)
        model.fit(X_train, y_train)
        metrics = evaluate_classifier(model, X_test, y_test)
        joblib.dump(model, run_dir / "model.joblib")

    metadata = {
        "run_id": run_id,
        "run_name": execution_cfg.get("run_name", "baseline"),
        "project": config.get("project", {}).get("name", "github-mlops-laboratory"),
        "phase": config.get("project", {}).get("phase", "phase-1-baseline"),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "task": data_cfg.get("task", "classification"),
        "model_type": model.__class__.__name__,
        "random_state": int(data_cfg["random_state"]),
        "train_samples": int(len(y_train)),
        "test_samples": int(len(y_test)),
        "n_features": int(X_train.shape[1]),
        "numpy_version": np.__version__,
        "python_version": platform.python_version(),
    }

    _json_dump(run_dir / "metrics.json", metrics)
    _json_dump(run_dir / "run_metadata.json", metadata)
    _json_dump(run_dir / "resource_profile.json", profile)
    return run_dir
