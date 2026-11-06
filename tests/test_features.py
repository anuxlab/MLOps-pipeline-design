import numpy as np
from mlops_lab.features import transform_features


def test_scaler_is_fit_and_outputs_are_finite():
    X_train = np.array([[0.0, 10.0], [2.0, 20.0], [4.0, 30.0]])
    X_test = np.array([[6.0, 40.0]])
    train, test, scaler = transform_features(X_train, X_test)
    assert np.allclose(train.mean(axis=0), 0.0)
    assert np.isfinite(test).all()
    assert scaler.mean_.tolist() == [2.0, 20.0]
