from pathlib import Path


class Dataset:
    def __init__(self, root: Path, split: str, shuffle: bool, cache: bool) -> None:
        self.root = Path(root)
        self.split = split
        self.shuffle = shuffle
        self.cache = cache
