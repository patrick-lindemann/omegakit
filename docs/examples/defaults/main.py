from pathlib import Path

from omegakit import load_config

config = load_config(Path(__file__).parent / "datasets.yaml")
datasets = config.datasets

assert dict(datasets.cifar) == {"path": "data/cifar", "split": "train", "shuffle": True}
assert datasets.imagenet.shuffle is False
assert datasets.test_set.split == "test"
# Scalars are not dict-valued siblings, so `$defaults` leaves them alone.
assert datasets.version == 3
assert "$defaults" not in datasets
