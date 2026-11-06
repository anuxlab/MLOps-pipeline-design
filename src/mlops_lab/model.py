from sklearn.linear_model import LogisticRegression


def build_model(config: dict):
    name = config.get("name", "logistic_regression").lower()
    if name != "logistic_regression":
        raise ValueError(f"Unsupported Phase 1 model: {name}")
    return LogisticRegression(
        max_iter=int(config.get("max_iter", 1000)),
        C=float(config.get("C", 1.0)),
        solver=str(config.get("solver", "lbfgs")),
        random_state=int(config.get("random_state", 42)),
    )
