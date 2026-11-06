import numpy as np
from sklearn.linear_model import LogisticRegression
from mlops_lab.evaluation import evaluate_classifier


def test_evaluation_returns_expected_metrics():
    X = np.array([[-2], [-1], [1], [2]], dtype=float)
    y = np.array([0, 0, 1, 1])
    model = LogisticRegression().fit(X, y)
    metrics = evaluate_classifier(model, X, y)
    assert metrics["accuracy"] == 1.0
    assert metrics["f1"] == 1.0
    assert metrics["roc_auc"] == 1.0
