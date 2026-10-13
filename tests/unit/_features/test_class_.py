import fractions
from types import ModuleType
from typing import Any

import pytest
from omegaconf import OmegaConf
from omegaconf.errors import InterpolationResolutionError, MissingMandatoryValue

from omegakit._core.error import OmegaKitBaseException
from omegakit._core.target import TargetNotFoundError, TargetSyntaxError
from omegakit._features.class_ import (
    ClassArguments,
    ClassInterpolationError,
    ClassMissingValueError,
    ClassSyntaxError,
    ClassTypeError,
    ConfigClassError,
    import_class,
    make_node,
    read_arguments,
)


def test_gives_the_target_of_a_node():
    content = {"half": {"$class": "fractions.Fraction", "numerator": 1}}
    config = OmegaConf.create(content)
    assert import_class(config.half) is fractions.Fraction
    assert config == content


def test_node_without_a_class_is_rejected():
    config = OmegaConf.create({"half": {"numerator": 1}})
    with pytest.raises(ClassSyntaxError):
        import_class(config.half)


def test_class_can_be_an_interpolation():
    config = OmegaConf.create(
        {"name": "Fraction", "half": {"$class": "fractions.${name}"}}
    )
    assert import_class(config.half) is fractions.Fraction


@pytest.mark.parametrize("value", [1, None, ["fractions.Fraction"]])
def test_class_that_is_not_a_string_is_rejected(value: Any):
    config = OmegaConf.create({"half": {"$class": value}})
    with pytest.raises(ClassTypeError):
        import_class(config.half)


def test_target_that_cannot_be_called_is_rejected():
    config = OmegaConf.create({"half": {"$class": "math.pi"}})
    with pytest.raises(ClassTypeError, match=r"\$ref"):
        import_class(config.half)


def test_target_with_from_config_need_not_be_callable(targets: ModuleType):
    config = OmegaConf.create({"item": {"$class": "config_targets.FACTORY"}})
    assert import_class(config.item) is targets.FACTORY


@pytest.mark.parametrize(
    ("import_path", "error_type"),
    [("Fraction", TargetSyntaxError), ("fractions.NoSuchName", TargetNotFoundError)],
)
def test_target_errors_pass_through(import_path: str, error_type: type[Exception]):
    config = OmegaConf.create({"half": {"$class": import_path}})
    with pytest.raises(error_type):
        import_class(config.half)


@pytest.mark.parametrize(
    ("value", "error_type"),
    [("???", ClassMissingValueError), ("${nowhere}", ClassInterpolationError)],
)
def test_key_that_cannot_be_read_is_rejected(value: str, error_type: type[Exception]):
    config = OmegaConf.create(
        {"a": {"$class": value}, "b": {"$class": "builtins.dict", "$partial": value}}
    )
    with pytest.raises(error_type, match=r"\$class"):
        import_class(config.a)
    with pytest.raises(error_type, match=r"\$partial"):
        read_arguments(config.b)


def test_arguments_are_the_keys_that_are_not_special():
    config = OmegaConf.create(
        {"$class": "fractions.Fraction", "$meta": "note", "numerator": 1, 2: "two"}
    )
    arguments = read_arguments(config)
    assert arguments.is_partial is False
    assert arguments.keys == ["numerator", 2]


def test_partial_is_read_from_the_node():
    config = OmegaConf.create(
        {
            "defer": True,
            "a": {"$class": "builtins.dict", "$partial": True, "n": 1},
            "b": {"$class": "builtins.dict", "$partial": False},
            "c": {"$class": "builtins.dict", "$partial": "${defer}"},
        }
    )
    assert read_arguments(config.a) == ClassArguments(True, ["n"])
    assert read_arguments(config.b) == ClassArguments(False, [])
    assert read_arguments(config.c) == ClassArguments(True, [])


def test_arguments_can_be_read_without_a_class():
    config = OmegaConf.create({"$partial": True, "width": 3})
    assert read_arguments(config) == ClassArguments(True, ["width"])


@pytest.mark.parametrize("value", ["true", 1, None, [True]])
def test_partial_that_is_not_a_boolean_is_rejected(value: Any):
    config = OmegaConf.create({"$class": "builtins.dict", "$partial": value})
    with pytest.raises(ClassTypeError):
        read_arguments(config)


@pytest.mark.parametrize("key", ["$ref", "$base", "$foo"])
def test_other_dollar_key_is_rejected(key: str):
    config = OmegaConf.create({"$class": "builtins.dict", key: "math.pi", "n": 1})
    with pytest.raises(ClassSyntaxError, match=rf"\{key}"):
        read_arguments(config)


def test_make_node_names_the_target():
    node = make_node(fractions.Fraction, numerator=1, denominator=2)
    assert node == {"$class": "fractions.Fraction", "numerator": 1, "denominator": 2}
    assert import_class(OmegaConf.create(node)) is fractions.Fraction


def test_make_node_rejects_a_target_that_is_not_at_module_level():
    with pytest.raises(ClassSyntaxError):
        make_node(fractions.Fraction.from_float)


@pytest.mark.parametrize(
    ("error_type", "parent_type"),
    [
        (ClassSyntaxError, ValueError),
        (ClassTypeError, TypeError),
        (ClassInterpolationError, InterpolationResolutionError),
        (ClassMissingValueError, MissingMandatoryValue),
    ],
)
def test_errors_are_also_builtin_or_omegaconf_errors(
    error_type: type[Exception], parent_type: type[Exception]
):
    assert issubclass(error_type, ConfigClassError)
    assert issubclass(error_type, OmegaKitBaseException)
    assert issubclass(error_type, parent_type)
