import numpy as np
from sklearn.preprocessing import StandardScaler


def transform_features(X_train, X_test):
    """Fit preprocessing on training data only, then transform both partitions."""
    scaler = StandardScaler()
    train_scaled = scaler.fit_transform(np.asarray(X_train))
    test_scaled = scaler.transform(np.asarray(X_test))
    if not np.isfinite(train_scaled).all() or not np.isfinite(test_scaled).all():
        raise ValueError("Feature transformation produced non-finite values.")
    return train_scaled, test_scaled, scaler
