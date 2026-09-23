import pytest
from omegaconf import OmegaConf
from omegaconf.errors import UnsupportedValueType

from omegakit import instantiate
from tests.helpers import (
    CONFIGURABLE_POINT,
    CONTAINER,
    FAILING,
    POINT,
    RECORDER,
    ConfigurablePoint,
    Container,
    Point,
)

# Contracts: §5 Instantiation, §6 Key namespace, §8 Error model.


def test_instantiate_builds_object():
    obj = instantiate({"$class": POINT, "x": 1, "y": 2})
    assert isinstance(obj, Point)
    assert (obj.x, obj.y) == (1, 2)


def test_instantiate_uses_from_config():
    obj = instantiate({"$class": CONFIGURABLE_POINT, "x": 3, "y": 4})
    assert isinstance(obj, ConfigurablePoint)
    assert (obj.x, obj.y) == (3, 4)


def test_instantiate_builds_nested_class():
    obj = instantiate(
        {
            "$class": CONTAINER,
            "name": "c",
            "point": {"$class": POINT, "x": 1, "y": 2},
        }
    )
    assert isinstance(obj, Container)
    assert isinstance(obj.point, Point)
    assert obj.point.x == 1


def test_instantiate_missing_class_raises():
    with pytest.raises(ValueError, match="Cannot instantiate config with no"):
        instantiate({"x": 1})


def test_instantiate_unknown_class_raises():
    with pytest.raises(ImportError):
        instantiate({"$class": "tests.helpers.DoesNotExist"})


def test_instantiate_applies_overrides():
    obj = instantiate({"$class": POINT, "x": 1, "y": 2}, overrides={"x": 10})
    assert obj.x == 10


def test_class_override_selects_new_class():
    cfg = OmegaConf.create({"$class": "missing.Original", "x": 1, "y": 2})
    obj = instantiate(cfg, overrides={"$class": POINT})
    assert isinstance(obj, Point)
    assert cfg["$class"] == "missing.Original"


def test_instantiate_does_not_mutate_input():
    config = OmegaConf.create({"$class": POINT, "x": "${y}", "y": 2})
    before = OmegaConf.to_yaml(config)
    instantiate(config)
    instantiate(config, overrides=["y=3"])
    assert OmegaConf.to_yaml(config) == before


def test_instantiate_resolves_interpolation():
    obj = instantiate(OmegaConf.create({"$class": POINT, "x": "${y}", "y": 2}))
    assert obj.x == 2


def test_instantiate_never_passes_meta():
    obj = instantiate(
        {
            "$class": CONTAINER,
            "$meta": {"a": 1},
            "name": "c",
            "point": {"$class": POINT, "$meta": 1, "x": 1, "y": 2},
        }
    )
    assert isinstance(obj.point, Point)


def test_instantiate_builds_classes_in_lists():
    obj = instantiate(
        {"$class": CONTAINER, "name": "c", "point": [{"$class": POINT, "x": 1, "y": 2}]}
    )
    assert isinstance(obj.point[0], Point)


def test_instantiate_duck_typed_from_config_receives_built_children():
    config, kwargs = instantiate(
        {"$class": RECORDER, "a": 1, "child": {"$class": POINT, "x": 1, "y": 2}}
    )
    assert config["a"] == 1
    assert isinstance(config["child"], Point)
    assert kwargs == {}


def test_instantiate_unknown_module_raises():
    with pytest.raises(ModuleNotFoundError):
        instantiate({"$class": "tests.does_not_exist.Thing"})


@pytest.mark.parametrize("wrap", [dict, OmegaConf.create])
def test_instantiate_raw_dict_resolves_like_dict_config(wrap):
    obj = instantiate(wrap({"$class": POINT, "x": "${y}", "y": 2}))
    assert obj.x == 2


def test_instantiate_raw_dict_rejects_unsupported_values():
    with pytest.raises(UnsupportedValueType):
        instantiate({"$class": POINT, "x": object(), "y": 2})


def test_instantiate_resolves_nested_escaped_interpolation_once():
    obj = instantiate(
        {
            "$class": CONTAINER,
            "name": "c",
            "point": {"$class": POINT, "x": r"\${y}", "y": 1},
        }
    )
    assert obj.point.x == "${y}"


def test_instantiate_error_keeps_type_and_message():
    with pytest.raises(TypeError) as info:
        instantiate({"$class": POINT, "x": 1})
    assert type(info.value) is TypeError
    assert str(info.value).startswith("Point.__init__()")


def test_instantiate_error_with_multi_argument_constructor_propagates():
    with pytest.raises(UnicodeDecodeError):
        instantiate({"$class": FAILING})


def test_instantiate_error_note_names_root():
    with pytest.raises(UnicodeDecodeError) as info:
        instantiate({"$class": FAILING})
    assert info.value.__notes__ == [f"while instantiating <root> ({FAILING})"]


def test_instantiate_error_note_names_nested_path():
    with pytest.raises(UnicodeDecodeError) as info:
        instantiate({"$class": CONTAINER, "name": "c", "point": {"$class": FAILING}})
    assert info.value.__notes__ == [f"while instantiating point ({FAILING})"]


def test_instantiate_error_note_names_list_index():
    with pytest.raises(UnicodeDecodeError) as info:
        instantiate(
            {"$class": CONTAINER, "name": "c", "point": [{"a": {"$class": FAILING}}]}
        )
    assert info.value.__notes__ == [f"while instantiating point.0.a ({FAILING})"]


def test_instantiate_error_from_from_config_gets_note():
    with pytest.raises(TypeError) as info:
        instantiate({"$class": CONFIGURABLE_POINT, "x": 1})
    assert info.value.__notes__ == [
        f"while instantiating <root> ({CONFIGURABLE_POINT})"
    ]


def test_instantiate_unknown_reserved_key_raises():
    with pytest.raises(ValueError, match="reserved"):
        instantiate({"$class": POINT, "$foo": 1, "x": 1, "y": 2})


def test_instantiate_class_with_ref_raises():
    with pytest.raises(ValueError, match="reserved"):
        instantiate({"$class": POINT, "$ref": "builtins.int", "x": 1, "y": 2})


def test_instantiate_unknown_reserved_key_in_plain_mapping_raises():
    with pytest.raises(ValueError, match="reserved"):
        instantiate({"$class": POINT, "x": {"$foo": 1}, "y": 2})


def test_instantiate_overrides_are_keyword_only():
    with pytest.raises(TypeError):
        instantiate({"$class": POINT, "x": 1, "y": 2}, Point, {"x": 3})  # pyright: ignore[reportCallIssue]


def test_instantiate_expected_is_not_checked_at_runtime():
    assert isinstance(instantiate({"$class": POINT, "x": 1, "y": 2}, Container), Point)
