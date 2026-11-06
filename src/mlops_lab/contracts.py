from dataclasses import dataclass, asdict
import numpy as np


@dataclass
class DataContractResult:
    passed: bool
    checks: dict
    errors: list[str]

    def to_dict(self):
        return asdict(self)


def validate_dataset(X, y, *, min_samples=100, expected_features=None) -> DataContractResult:
    errors = []
    checks = {}
    X = np.asarray(X)
    y = np.asarray(y)

    checks["two_dimensional_features"] = X.ndim == 2
    if X.ndim != 2:
        errors.append("Features must be a two-dimensional matrix.")
        n_rows, n_features = 0, 0
    else:
        n_rows, n_features = X.shape

    checks["one_dimensional_target"] = y.ndim == 1
    if y.ndim != 1:
        errors.append("Target must be a one-dimensional vector.")

    checks["matching_row_counts"] = X.ndim == 2 and y.ndim == 1 and n_rows == len(y)
    if not checks["matching_row_counts"]:
        errors.append("Feature and target row counts must match.")

    checks["minimum_sample_count"] = X.ndim == 2 and n_rows >= min_samples
    if not checks["minimum_sample_count"]:
        errors.append(f"Dataset must contain at least {min_samples} rows.")

    checks["expected_feature_count"] = (
        expected_features is None or (X.ndim == 2 and n_features == expected_features)
    )
    if not checks["expected_feature_count"]:
        errors.append(f"Expected {expected_features} features; received {n_features}.")

    checks["finite_features"] = bool(X.ndim == 2 and np.isfinite(X).all())
    if not checks["finite_features"]:
        errors.append("Features contain NaN or infinite values.")

    checks["valid_target_values"] = bool(y.ndim == 1 and len(np.unique(y)) >= 2)
    if not checks["valid_target_values"]:
        errors.append("Target must contain at least two distinct classes.")

    return DataContractResult(passed=not errors, checks=checks, errors=errors)
