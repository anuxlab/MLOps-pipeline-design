import numpy as np
from mlops_lab.drift import detect_feature_drift


def test_drift_detector_flags_shifted_features():
    rng = np.random.default_rng(123)
    reference = rng.normal(0, 1, size=(1000, 5))
    current = reference.copy()
    current[:, :3] += 2.0
    result = detect_feature_drift(reference, current, alpha=0.01, min_drifted_fraction=0.30)
    assert result["drift_detected"] is True
    assert result["drifted_features"] >= 3


def test_drift_detector_does_not_flag_identical_samples():
    rng = np.random.default_rng(123)
    reference = rng.normal(size=(500, 4))
    result = detect_feature_drift(reference, reference.copy())
    assert result["drift_detected"] is False
