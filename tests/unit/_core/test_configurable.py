from omegakit._core.configurable import Configurable


class _Layer(Configurable):
    def __init__(self, width: int, depth: int = 2, name: str = "layer"):
        self.width = width
        self.depth = depth
        self.name = name


def test_from_config_passes_the_items_of_a_mapping():
    layer = _Layer.from_config({"width": 3, "depth": 5})
    assert (layer.width, layer.depth, layer.name) == (3, 5, "layer")


def test_from_config_passes_extra_arguments():
    layer = _Layer.from_config({"width": 3}, name="first", depth=7)
    assert (layer.width, layer.depth, layer.name) == (3, 7, "first")
