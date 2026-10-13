import fractions
from types import ModuleType
from typing import Any

import pytest
from omegaconf import OmegaConf
from omegaconf.errors import InterpolationResolutionError, MissingMandatoryValue

from omegakit._core.error import OmegaKitBaseException
from omegakit._core.utils.locate import (
    QualifiedNameNotFoundError,
    QualifiedNameSyntaxError,
)
from omegakit._features.target import (
    ConfigTargetError,
    TargetArguments,
    TargetInterpolationError,
    TargetMissingValueError,
    TargetSyntaxError,
    TargetTypeError,
    import_target,
    make_node,
    read_arguments,
)


def test_gives_the_target_of_a_node():
    content = {"half": {"$target": "fractions.Fraction", "numerator": 1}}
    config = OmegaConf.create(content)
    assert import_target(config.half) is fractions.Fraction
    assert config == content


def test_node_without_a_target_is_rejected():
    config = OmegaConf.create({"half": {"numerator": 1}})
    with pytest.raises(TargetSyntaxError):
        import_target(config.half)


def test_target_can_be_an_interpolation():
    config = OmegaConf.create(
        {"name": "Fraction", "half": {"$target": "fractions.${name}"}}
    )
    assert import_target(config.half) is fractions.Fraction


@pytest.mark.parametrize("value", [1, None, ["fractions.Fraction"]])
def test_target_that_is_not_a_string_is_rejected(value: Any):
    config = OmegaConf.create({"half": {"$target": value}})
    with pytest.raises(TargetTypeError):
        import_target(config.half)


def test_target_that_cannot_be_called_is_rejected():
    config = OmegaConf.create({"half": {"$target": "math.pi"}})
    with pytest.raises(TargetTypeError, match=r"\$symbol"):
        import_target(config.half)


def test_target_with_from_config_need_not_be_callable(targets: ModuleType):
    config = OmegaConf.create({"item": {"$target": "config_targets.FACTORY"}})
    assert import_target(config.item) is targets.FACTORY


@pytest.mark.parametrize(
    ("qualified_name", "error_type"),
    [
        ("Fraction", QualifiedNameSyntaxError),
        ("fractions.NoSuchName", QualifiedNameNotFoundError),
    ],
)
def test_locate_errors_pass_through(qualified_name: str, error_type: type[Exception]):
    config = OmegaConf.create({"half": {"$target": qualified_name}})
    with pytest.raises(error_type):
        import_target(config.half)


@pytest.mark.parametrize(
    ("value", "error_type"),
    [("???", TargetMissingValueError), ("${nowhere}", TargetInterpolationError)],
)
def test_key_that_cannot_be_read_is_rejected(value: str, error_type: type[Exception]):
    config = OmegaConf.create(
        {"a": {"$target": value}, "b": {"$target": "builtins.dict", "$partial": value}}
    )
    with pytest.raises(error_type, match=r"\$target"):
        import_target(config.a)
    with pytest.raises(error_type, match=r"\$partial"):
        read_arguments(config.b)


def test_arguments_are_the_keys_that_are_not_special():
    config = OmegaConf.create(
        {"$target": "fractions.Fraction", "$meta": "note", "numerator": 1, 2: "two"}
    )
    arguments = read_arguments(config)
    assert arguments.is_partial is False
    assert arguments.keys == ["numerator", 2]


def test_partial_is_read_from_the_node():
    config = OmegaConf.create(
        {
            "defer": True,
            "a": {"$target": "builtins.dict", "$partial": True, "n": 1},
            "b": {"$target": "builtins.dict", "$partial": False},
            "c": {"$target": "builtins.dict", "$partial": "${defer}"},
        }
    )
    assert read_arguments(config.a) == TargetArguments(True, ["n"], False)
    assert read_arguments(config.b) == TargetArguments(False, [], False)
    assert read_arguments(config.c) == TargetArguments(True, [], False)


def test_arguments_can_be_read_without_a_target():
    config = OmegaConf.create({"$partial": True, "width": 3})
    assert read_arguments(config) == TargetArguments(True, ["width"], False)


def test_args_are_no_keyword_argument():
    config = OmegaConf.create({"$target": "builtins.int", "$args": ["ff"], "base": 16})
    arguments = read_arguments(config)
    assert arguments.has_args
    assert arguments.keys == ["base"]


@pytest.mark.parametrize("value", ["true", 1, None, [True]])
def test_partial_that_is_not_a_boolean_is_rejected(value: Any):
    config = OmegaConf.create({"$target": "builtins.dict", "$partial": value})
    with pytest.raises(TargetTypeError):
        read_arguments(config)


@pytest.mark.parametrize("key", ["$symbol", "$base", "$foo"])
def test_other_dollar_key_is_rejected(key: str):
    config = OmegaConf.create({"$target": "builtins.dict", key: "math.pi", "n": 1})
    with pytest.raises(TargetSyntaxError, match=rf"\{key}"):
        read_arguments(config)


def test_make_node_names_the_target():
    node = make_node(fractions.Fraction, numerator=1, denominator=2)
    assert node == {"$target": "fractions.Fraction", "numerator": 1, "denominator": 2}
    assert import_target(OmegaConf.create(node)) is fractions.Fraction


def test_make_node_writes_positional_arguments_to_args():
    node = make_node(fractions.Fraction, 1, denominator=2)
    assert node == {"$target": "fractions.Fraction", "denominator": 2, "$args": [1]}
    assert "$args" not in make_node(fractions.Fraction, numerator=1)


def test_make_node_rejects_a_target_that_is_not_at_module_level():
    with pytest.raises(TargetSyntaxError):
        make_node(fractions.Fraction.from_float)


@pytest.mark.parametrize(
    ("error_type", "parent_type"),
    [
        (TargetSyntaxError, ValueError),
        (TargetTypeError, TypeError),
        (TargetInterpolationError, InterpolationResolutionError),
        (TargetMissingValueError, MissingMandatoryValue),
    ],
)
def test_errors_are_also_builtin_or_omegaconf_errors(
    error_type: type[Exception], parent_type: type[Exception]
):
    assert issubclass(error_type, ConfigTargetError)
    assert issubclass(error_type, OmegaKitBaseException)
    assert issubclass(error_type, parent_type)
