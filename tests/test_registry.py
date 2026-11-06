import json
from pathlib import Path
import joblib, numpy as np, pytest
from sklearn.linear_model import LogisticRegression
from mlops_lab.registry import register_and_deploy, load_environment_model, sha256

def source_dir(tmp_path, promoted=True):
    src=tmp_path/"ct"; src.mkdir()
    X=np.array([[0,0],[0,1],[1,0],[1,1],[2,1],[2,2]],dtype=float); y=np.array([0,0,0,1,1,1])
    model=LogisticRegression().fit(X,y); joblib.dump(model,src/"candidate_model.joblib")
    (src/"ct_report.json").write_text(json.dumps({"candidate":{"promoted":promoted,"metrics":{"accuracy":0.9}}}))
    return src

def test_register_and_load_environment(tmp_path):
    dest=register_and_deploy(source_dir(tmp_path),tmp_path/"registry","dev")
    model,manifest=load_environment_model(tmp_path/"registry","dev")
    assert manifest["version"]==dest.name
    assert model.predict([[2,2]])[0]==1
    assert sha256(dest/"model.joblib")==manifest["model_sha256"]

def test_reject_unpromoted_candidate(tmp_path):
    with pytest.raises(ValueError,match="approved promoted"):
        register_and_deploy(source_dir(tmp_path,False),tmp_path/"registry","dev")

def test_checksum_tampering_rejected(tmp_path):
    dest=register_and_deploy(source_dir(tmp_path),tmp_path/"registry","dev")
    (dest/"model.joblib").write_bytes(b"tampered")
    with pytest.raises(ValueError,match="checksum"):
        load_environment_model(tmp_path/"registry","dev")

def test_resolve_nested_downloaded_artifact(tmp_path):
    outer=tmp_path/"download"; nested=outer/"20261106T000000Z-run"; nested.mkdir(parents=True)
    src=source_dir(tmp_path)
    for filename in ("candidate_model.joblib","ct_report.json"):
        (nested/filename).write_bytes((src/filename).read_bytes())
    dest=register_and_deploy(outer,tmp_path/"registry","staging")
    assert dest.is_dir()
