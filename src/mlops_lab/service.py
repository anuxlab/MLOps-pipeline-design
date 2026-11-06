"""Minimal prediction API for a selected registry environment."""
import os
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from .registry import load_environment_model

REGISTRY_DIR=os.getenv("MLOPS_REGISTRY_DIR","model_registry")
ENVIRONMENT=os.getenv("MLOPS_ENVIRONMENT","dev")
app=FastAPI(title="MLOps Laboratory Prediction API",version="1.0.0")

class PredictionRequest(BaseModel):
    features: list[float] = Field(min_length=1)

@app.get("/health")
def health():
    try:
        _,manifest=load_environment_model(REGISTRY_DIR,ENVIRONMENT)
        return {"status":"ok","environment":ENVIRONMENT,"model_version":manifest["version"]}
    except Exception as exc:
        raise HTTPException(status_code=503,detail=f"Model unavailable: {exc}")

@app.post("/predict")
def predict(request: PredictionRequest):
    try:
        model,manifest=load_environment_model(REGISTRY_DIR,ENVIRONMENT)
        x=np.asarray(request.features,dtype=float).reshape(1,-1)
        if x.shape[1] != int(manifest.get("n_features",x.shape[1])):
            raise ValueError("Feature count mismatch")
        if not np.isfinite(x).all(): raise ValueError("Features must be finite")
        estimator=model.get("model") if isinstance(model,dict) else model
        scaler=model.get("scaler") if isinstance(model,dict) else None
        if scaler is not None: x=scaler.transform(x)
        prediction=int(estimator.predict(x)[0])
        probabilities=estimator.predict_proba(x)[0].tolist()
        return {"prediction":prediction,"probabilities":probabilities,"model_version":manifest["version"]}
    except Exception as exc:
        raise HTTPException(status_code=400,detail=str(exc))
