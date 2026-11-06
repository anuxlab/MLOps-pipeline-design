import numpy as np
from scipy.stats import ks_2samp


def detect_feature_drift(reference, current, *, alpha=0.01, min_drifted_fraction=0.30):
    """Detect univariate feature distribution changes using two-sample KS tests.

    The result is a screening signal, not proof of concept drift or causality.
    """
    reference = np.asarray(reference, dtype=float)
    current = np.asarray(current, dtype=float)
    if reference.ndim != 2 or current.ndim != 2:
        raise ValueError("Reference and current features must be 2D matrices.")
    if reference.shape[1] != current.shape[1]:
        raise ValueError("Reference and current feature counts must match.")
    if not np.isfinite(reference).all() or not np.isfinite(current).all():
        raise ValueError("Drift detection requires finite feature values.")

    features = []
    for index in range(reference.shape[1]):
        result = ks_2samp(reference[:, index], current[:, index], alternative="two-sided")
        features.append({
            "feature_index": int(index),
            "ks_statistic": float(result.statistic),
            "p_value": float(result.pvalue),
            "drift_detected": bool(result.pvalue < alpha),
        })
    drifted = sum(item["drift_detected"] for item in features)
    fraction = drifted / max(len(features), 1)
    return {
        "method": "two_sample_kolmogorov_smirnov",
        "alpha": float(alpha),
        "min_drifted_fraction": float(min_drifted_fraction),
        "n_features": len(features),
        "drifted_features": int(drifted),
        "drifted_fraction": float(fraction),
        "drift_detected": bool(fraction >= min_drifted_fraction),
        "features": features,
        "interpretation": (
            "Feature distribution drift signal detected."
            if fraction >= min_drifted_fraction
            else "No aggregate feature drift signal detected."
        ),
    }
