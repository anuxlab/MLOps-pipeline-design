import json, joblib, numpy as np
from fastapi.testclient import TestClient
from sklearn.linear_model import LogisticRegression
from mlops_lab import service

def test_health_and_prediction(tmp_path, monkeypatch):
    registry=tmp_path/"registry"; version="vtest"; dest=registry/"models"/"m"/version
    dest.mkdir(parents=True)
    X=np.array([[0,0],[0,1],[1,0],[1,1],[2,1],[2,2]],float); y=np.array([0,0,0,1,1,1])
    model=LogisticRegression().fit(X,y); joblib.dump(model,dest/"model.joblib")
    from mlops_lab.registry import sha256
    (dest/"manifest.json").write_text(json.dumps({"version":version,"model_sha256":sha256(dest/"model.joblib")}))
    env=registry/"environments"; env.mkdir()
    (env/"dev.json").write_text(json.dumps({"model":"models/m/vtest/model.joblib","manifest":"models/m/vtest/manifest.json"}))
    monkeypatch.setattr(service,"REGISTRY_DIR",str(registry))
    monkeypatch.setattr(service,"ENVIRONMENT","dev")
    client=TestClient(service.app)
    assert client.get("/health").status_code==200
    result=client.post("/predict",json={"features":[2,2]})
    assert result.status_code==200 and result.json()["prediction"]==1
