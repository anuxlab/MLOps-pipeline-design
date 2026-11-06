from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split


def generate_classification_data(config: dict):
    X, y = make_classification(
        n_samples=int(config["n_samples"]),
        n_features=int(config["n_features"]),
        n_informative=int(config["n_informative"]),
        n_redundant=int(config["n_redundant"]),
        n_classes=int(config["n_classes"]),
        class_sep=float(config["class_sep"]),
        flip_y=float(config["flip_y"]),
        random_state=int(config["random_state"]),
    )
    return train_test_split(
        X,
        y,
        test_size=float(config["test_size"]),
        random_state=int(config["random_state"]),
        stratify=y,
    )
