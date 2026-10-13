import math
from typing import Any

import pytest
from omegaconf import OmegaConf
from omegaconf.errors import InterpolationResolutionError, MissingMandatoryValue

from omegakit._core.error import OmegaKitBaseException
from omegakit._core.locate import QualifiedNameNotFoundError, QualifiedNameSyntaxError
from omegakit._features.symbol import (
    ConfigSymbolError,
    SymbolInterpolationError,
    SymbolMissingValueError,
    SymbolSyntaxError,
    SymbolTypeError,
    import_symbol,
)


def test_gives_the_object_of_a_node():
    config = OmegaConf.create({"loss": {"$symbol": "math.sqrt"}})
    assert import_symbol(config.loss) is math.sqrt
    assert config == {"loss": {"$symbol": "math.sqrt"}}


def test_node_without_a_symbol_is_rejected():
    config = OmegaConf.create({"loss": {"reduction": "mean"}})
    with pytest.raises(SymbolSyntaxError):
        import_symbol(config.loss)


def test_meta_next_to_a_symbol_is_allowed():
    config = OmegaConf.create({"loss": {"$symbol": "math.sqrt", "$meta": {"doc": "x"}}})
    assert import_symbol(config.loss) is math.sqrt


def test_symbol_can_be_an_interpolation():
    config = OmegaConf.create({"name": "sqrt", "loss": {"$symbol": "math.${name}"}})
    assert import_symbol(config.loss) is math.sqrt


def test_other_key_next_to_a_symbol_is_rejected():
    config = OmegaConf.create({"loss": {"$symbol": "math.sqrt", "reduction": "mean"}})
    with pytest.raises(SymbolSyntaxError, match="reduction"):
        import_symbol(config.loss)


@pytest.mark.parametrize("value", [1, None, ["math.sqrt"], {"path": "math.sqrt"}])
def test_symbol_that_is_not_a_string_is_rejected(value: Any):
    config = OmegaConf.create({"loss": {"$symbol": value}})
    with pytest.raises(SymbolTypeError):
        import_symbol(config.loss)


def test_missing_symbol_is_rejected():
    config = OmegaConf.create({"loss": {"$symbol": "???"}})
    with pytest.raises(SymbolMissingValueError):
        import_symbol(config.loss)


def test_failing_interpolation_is_rejected():
    config = OmegaConf.create({"loss": {"$symbol": "${nowhere}"}})
    with pytest.raises(SymbolInterpolationError):
        import_symbol(config.loss)


@pytest.mark.parametrize(
    ("qualified_name", "error_type"),
    [
        ("sqrt", QualifiedNameSyntaxError),
        ("math.no_such_name", QualifiedNameNotFoundError),
    ],
)
def test_locate_errors_pass_through(qualified_name: str, error_type: type[Exception]):
    config = OmegaConf.create({"loss": {"$symbol": qualified_name}})
    with pytest.raises(error_type):
        import_symbol(config.loss)


@pytest.mark.parametrize(
    ("error_type", "parent_type"),
    [
        (SymbolSyntaxError, ValueError),
        (SymbolTypeError, TypeError),
        (SymbolInterpolationError, InterpolationResolutionError),
        (SymbolMissingValueError, MissingMandatoryValue),
    ],
)
def test_errors_are_also_builtin_or_omegaconf_errors(
    error_type: type[Exception], parent_type: type[Exception]
):
    assert issubclass(error_type, ConfigSymbolError)
    assert issubclass(error_type, OmegaKitBaseException)
    assert issubclass(error_type, parent_type)
