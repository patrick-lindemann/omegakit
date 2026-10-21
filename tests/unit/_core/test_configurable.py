from dataclasses import dataclass
from typing import Any, TypedDict

import pytest

from omegakit._core.configurable import Configurable
from omegakit._core.errors import SchemaDefinitionError


class _Layer(Configurable):
    def __init__(self, width: int, depth: int = 2, name: str = "layer"):
        self.width = width
        self.depth = depth
        self.name = name


class _LayerConfig(TypedDict):
    width: int


@dataclass
class _Section:
    width: int = 1


def test_from_config_passes_the_items_of_a_mapping():
    layer = _Layer.from_config({"width": 3, "depth": 5})
    assert (layer.width, layer.depth, layer.name) == (3, 5, "layer")


def test_from_config_passes_extra_arguments():
    layer = _Layer.from_config({"width": 3}, name="first", depth=7)
    assert (layer.width, layer.depth, layer.name) == (3, 7, "first")


@pytest.mark.parametrize("schema", [dict, _Section, _Section()])
def test_schema_must_be_a_typed_dict(schema: Any):
    with pytest.raises(SchemaDefinitionError, match="`Broken` must be a `TypedDict`"):
        type("Broken", (Configurable,), {}, schema=schema)


def test_unknown_class_keyword_is_rejected():
    with pytest.raises(TypeError, match="shema"):
        type("Misspelled", (Configurable,), {}, shema=_LayerConfig)


class _Plugin:
    def __init_subclass__(cls, *, name: str = "", **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls.name = name


def test_base_with_its_own_class_keywords_comes_first():
    class Model(_Plugin, Configurable, name="mlp", schema=_LayerConfig):
        pass

    assert Model.name == "mlp"
