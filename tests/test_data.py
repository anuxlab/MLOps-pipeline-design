from mlops_lab.data import generate_classification_data


def test_classification_data_shapes_and_reproducibility():
    config = {
        "n_samples": 200, "n_features": 10, "n_informative": 5,
        "n_redundant": 2, "n_classes": 2, "class_sep": 1.0,
        "flip_y": 0.01, "random_state": 7, "test_size": 0.2
    }
    first = generate_classification_data(config)
    second = generate_classification_data(config)
    assert first[0].shape == (160, 10)
    assert first[1].shape == (40, 10)
    assert (first[0] == second[0]).all()
    assert (first[3] == second[3]).all()
