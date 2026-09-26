from dataclasses import dataclass
from pathlib import Path

from omegakit import Configurable, ConfigValidationError, check_schema, instantiate


@dataclass
class DatasetConfig:
    root: Path
    batch_size: int = 32
    shuffle: bool = True


class Dataset(Configurable[DatasetConfig]):
    def __init__(self, root: Path, batch_size: int, shuffle: bool) -> None:
        self.root = root
        self.batch_size = batch_size
        self.shuffle = shuffle


check_schema(Dataset)

dataset = instantiate(
    {"$class": "__main__.Dataset", "root": "data/train", "batch_size": "64"}, Dataset
)
assert dataset.root == Path("data/train")
assert dataset.batch_size == 64

try:
    instantiate({"$class": "__main__.Dataset", "root": "data", "batch": 64})
except ConfigValidationError as error:
    assert "'batch'" in str(error)
else:
    raise AssertionError("an unknown field must fail")
