"""Filesystem model registry and controlled environment promotion."""
from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

import joblib


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_candidate(source_dir: Path) -> tuple[Path, Path, Path]:
    """Find exactly one co-located model/report/manifest triplet recursively."""
    manifests = list(source_dir.rglob("model_manifest.json"))
    valid = []
    for manifest_path in manifests:
        parent = manifest_path.parent
        model_path = parent / "candidate_model.joblib"
        report_path = parent / "ct_report.json"
        if model_path.is_file() and report_path.is_file():
            valid.append((model_path, report_path, manifest_path))
    if len(valid) != 1:
        raise FileNotFoundError(
            "Expected exactly one co-located candidate_model.joblib, "
            "ct_report.json and model_manifest.json triplet; "
            f"found {len(valid)}"
        )
    return valid[0]


def register_and_deploy(
    source_dir: str | Path,
    registry_dir: str | Path,
    target_environment: str,
    model_name: str = "mlops-binary-classifier",
    expected_source_run_id: str | None = None,
) -> Path:
    if target_environment not in {"dev", "staging", "prod"}:
        raise ValueError("target_environment must be dev, staging, or prod")

    source = Path(source_dir)
    model_path, report_path, manifest_path = _resolve_candidate(source)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    source_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if report.get("status") != "passed":
        raise ValueError("CT report status is not passed")
    candidate = report.get("candidate", {})
    if not candidate.get("trained") or not candidate.get("promoted"):
        raise ValueError("CT report does not contain an approved promoted candidate that was trained")

    if source_manifest.get("pipeline") != "continuous_training":
        raise ValueError("Candidate manifest pipeline is not continuous_training")
    if source_manifest.get("candidate_promoted") is not True:
        raise ValueError("Candidate manifest does not confirm promotion")
    if source_manifest.get("model_file") != model_path.name:
        raise ValueError("Candidate manifest model filename mismatch")
    if source_manifest.get("report_file") != report_path.name:
        raise ValueError("Candidate manifest report filename mismatch")
    if source_manifest.get("checksum_algorithm") != "sha256":
        raise ValueError("Unsupported candidate checksum algorithm")

    actual_digest = sha256(model_path)
    if actual_digest != source_manifest.get("model_sha256"):
        raise ValueError("Candidate model checksum verification failed")

    source_run_id = source_manifest.get("source_run_id")
    report_run_id = (report.get("source") or {}).get("github_run_id")
    if source_run_id and report_run_id and str(source_run_id) != str(report_run_id):
        raise ValueError("Candidate manifest and CT report source run IDs do not match")
    if expected_source_run_id and str(report_run_id) != str(expected_source_run_id):
        raise ValueError("CT report source run ID does not match the selected Phase 3 run")
    if expected_source_run_id and str(source_run_id) != str(expected_source_run_id):
        raise ValueError(
            f"Candidate source run ID mismatch: expected {expected_source_run_id}, "
            f"found {source_run_id}"
        )

    metrics = candidate.get("metrics", {})
    if not metrics:
        raise ValueError("Candidate metrics missing from CT report")

    artifact = joblib.load(model_path)
    estimator = artifact.get("model") if isinstance(artifact, dict) else artifact
    scaler = artifact.get("scaler") if isinstance(artifact, dict) else None
    if not hasattr(estimator, "predict") or not hasattr(estimator, "predict_proba"):
        raise ValueError("Candidate does not implement the expected prediction interface")
    if scaler is not None and not hasattr(scaler, "transform"):
        raise ValueError("Candidate scaler does not implement transform")

    registry = Path(registry_dir)
    versions = registry / "models" / model_name
    versions.mkdir(parents=True, exist_ok=True)
    version = f"v{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    destination = versions / version
    destination.mkdir()

    shutil.copy2(model_path, destination / "model.joblib")
    shutil.copy2(manifest_path, destination / "source_model_manifest.json")
    deployed_manifest = {
        "model_name": model_name,
        "version": version,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_ct_run_id": source_run_id,
        "source_commit": source_manifest.get("source_commit"),
        "source_branch": source_manifest.get("source_branch"),
        "source_artifact_manifest": "source_model_manifest.json",
        "model_file": "model.joblib",
        "model_sha256": sha256(destination / "model.joblib"),
        "metrics": metrics,
        "environment": target_environment,
        "n_features": int(
            getattr(scaler, "n_features_in_", getattr(estimator, "n_features_in_", 0))
        ),
        "decision": "registered_and_deployed",
        "schema_version": 2,
    }
    (destination / "manifest.json").write_text(
        json.dumps(deployed_manifest, indent=2) + "\n", encoding="utf-8"
    )

    environment_dir = registry / "environments"
    environment_dir.mkdir(parents=True, exist_ok=True)
    pointer = {
        "environment": target_environment,
        "model_name": model_name,
        "version": version,
        "manifest": str(Path("models") / model_name / version / "manifest.json"),
        "model": str(Path("models") / model_name / version / "model.joblib"),
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    (environment_dir / f"{target_environment}.json").write_text(
        json.dumps(pointer, indent=2) + "\n", encoding="utf-8"
    )
    return destination


def load_environment_model(registry_dir: str | Path, environment: str):
    if environment not in {"dev", "staging", "prod"}:
        raise ValueError("Invalid environment")
    registry = Path(registry_dir)
    pointer = json.loads(
        (registry / "environments" / f"{environment}.json").read_text(encoding="utf-8")
    )
    model_path = registry / pointer["model"]
    manifest = json.loads((registry / pointer["manifest"]).read_text(encoding="utf-8"))
    if sha256(model_path) != manifest["model_sha256"]:
        raise ValueError("Model checksum verification failed")
    return joblib.load(model_path), manifest
