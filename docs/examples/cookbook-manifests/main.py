from pathlib import Path

from data import Dataset

from omegakit import instantiate, load_config

config = load_config(Path(__file__).parent / "manifest.yaml")
datasets = {name: instantiate(node, Dataset) for name, node in config.datasets.items()}

assert set(datasets) == {"cifar", "cifar_test", "imagenet"}
assert datasets["cifar_test"].root == Path("/data/cifar")
assert (datasets["cifar_test"].split, datasets["cifar_test"].shuffle) == ("test", False)
assert datasets["imagenet"].cache is True
