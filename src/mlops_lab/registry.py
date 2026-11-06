"""Filesystem model registry and controlled environment promotion."""
from __future__ import annotations
import hashlib, json, shutil, uuid
from datetime import datetime, timezone
from pathlib import Path
import joblib
import numpy as np

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024), b""): h.update(chunk)
    return h.hexdigest()

def register_and_deploy(source_dir: str|Path, registry_dir: str|Path, target_environment: str,
                        model_name: str="mlops-binary-classifier") -> Path:
    if target_environment not in {"dev","staging","prod"}:
        raise ValueError("target_environment must be dev, staging, or prod")
    source=Path(source_dir)
    model=source/"candidate_model.joblib"; report_path=source/"ct_report.json"
    if not model.is_file() or not report_path.is_file():
        # download-artifact may preserve the CT run directory beneath the destination.
        matches=[item.parent for item in source.rglob("ct_report.json")
                 if (item.parent/"candidate_model.joblib").is_file()]
        if len(matches)==1:
            source=matches[0]; model=source/"candidate_model.joblib"; report_path=source/"ct_report.json"
        else:
            raise FileNotFoundError(
                "Source must contain one candidate_model.joblib + ct_report.json pair; "
                f"found {len(matches)} candidate pairs"
            )
    report=json.loads(report_path.read_text())
    candidate=report.get("candidate",{})
    if not candidate.get("promoted"):
        raise ValueError("CT report does not contain an approved promoted candidate")
    metrics=candidate.get("metrics",{})
    if not metrics:
        raise ValueError("Candidate metrics missing from CT report")
    # Load once to reject corrupt/incompatible serialized artifacts.
    artifact=joblib.load(model)
    estimator=artifact.get("model") if isinstance(artifact,dict) else artifact
    scaler=artifact.get("scaler") if isinstance(artifact,dict) else None
    if not hasattr(estimator,"predict") or not hasattr(estimator,"predict_proba"):
        raise ValueError("Candidate does not implement the expected prediction interface")
    if scaler is not None and not hasattr(scaler,"transform"):
        raise ValueError("Candidate scaler does not implement transform")
    registry=Path(registry_dir); versions=registry/"models"/model_name
    versions.mkdir(parents=True,exist_ok=True)
    version=f"v{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    dest=versions/version; dest.mkdir()
    shutil.copy2(model,dest/"model.joblib")
    manifest={
      "model_name":model_name,"version":version,"created_at_utc":datetime.now(timezone.utc).isoformat(),
      "source_ct_run":source.name,"source_report":"ct_report.json",
      "model_file":"model.joblib","model_sha256":sha256(dest/"model.joblib"),
      "metrics":metrics,"environment":target_environment,
      "n_features":int(getattr(scaler,"n_features_in_",getattr(estimator,"n_features_in_",0))),
      "decision":"registered_and_deployed","schema_version":1
    }
    (dest/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    env_dir=registry/"environments"; env_dir.mkdir(parents=True,exist_ok=True)
    pointer={"environment":target_environment,"model_name":model_name,"version":version,
             "manifest":str(Path("models")/model_name/version/"manifest.json"),
             "model":str(Path("models")/model_name/version/"model.joblib"),
             "updated_at_utc":datetime.now(timezone.utc).isoformat()}
    (env_dir/f"{target_environment}.json").write_text(json.dumps(pointer,indent=2)+"\n")
    return dest

def load_environment_model(registry_dir: str|Path, environment: str):
    if environment not in {"dev","staging","prod"}: raise ValueError("Invalid environment")
    registry=Path(registry_dir); pointer=json.loads((registry/"environments"/f"{environment}.json").read_text())
    model_path=registry/pointer["model"]
    manifest=json.loads((registry/pointer["manifest"]).read_text())
    if sha256(model_path)!=manifest["model_sha256"]: raise ValueError("Model checksum verification failed")
    return joblib.load(model_path), manifest
