import numpy as np
from mlops_lab.contracts import validate_dataset


def test_valid_dataset_passes_contract():
    X = np.ones((120, 4))
    y = np.array([0, 1] * 60)
    result = validate_dataset(X, y, min_samples=100, expected_features=4)
    assert result.passed
    assert all(result.checks.values())


def test_nan_and_wrong_feature_count_are_rejected():
    X = np.ones((120, 4))
    X[0, 0] = np.nan
    y = np.array([0, 1] * 60)
    result = validate_dataset(X, y, expected_features=5)
    assert not result.passed
    assert not result.checks["finite_features"]
    assert not result.checks["expected_feature_count"]
