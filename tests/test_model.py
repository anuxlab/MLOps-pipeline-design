import numpy as np
from mlops_lab.model import build_model


def test_logistic_regression_model_fits():
    model = build_model({"name": "logistic_regression", "max_iter": 200, "C": 1.0})
    X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], dtype=float)
    y = np.array([0, 0, 1, 1])
    model.fit(X, y)
    assert model.predict(X).shape == (4,)


def test_unknown_model_rejected():
    try:
        build_model({"name": "unknown"})
    except ValueError as exc:
        assert "Unsupported" in str(exc)
    else:
        raise AssertionError("Expected unsupported model to raise ValueError")
