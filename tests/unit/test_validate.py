import dataclasses
from collections.abc import Callable
from types import ModuleType
from typing import Any, Protocol

import pytest
from omegaconf import DictConfig, OmegaConf
from omegaconf.errors import InterpolationResolutionError, MissingMandatoryValue

from omegakit._core.error import OmegaKitBaseException
from omegakit._core.target import TargetNotFoundError
from omegakit._features.class_ import (
    ClassMissingValueError,
    ClassSyntaxError,
    ClassTypeError,
)
from omegakit._features.symbol import SymbolSyntaxError
from omegakit.schema import (
    SchemaDefinitionError,
    SchemaKeyError,
    SchemaMissingValueError,
    SchemaTypeError,
    SchemaValueError,
)
from omegakit.validate import (
    ConfigValidationError,
    ValidationCycleError,
    ValidationInterpolationError,
    ValidationMissingValueError,
    ValidationSyntaxError,
    validate,
)


class _Greeter(Protocol):
    name: str


type _Mapping = dict[str, Any] | None


@dataclasses.dataclass
class _Parts:
    greeter: _Greeter | None = None
    alias: _Mapping = None
    factory: Callable[..., Any] | None = None
    kind: type[int] | None = None
    plain: list | None = None
    options: dict[str, dict[str, int]] | None = None


def _report(error: BaseException) -> str:
    return "\n".join([str(error), *getattr(error, "__notes__", [])])


def test_accepts_a_valid_config_and_calls_nothing(targets: ModuleType):
    content = {
        "width": 3,
        "model": {
            "$class": "config_targets.Item",
            "$meta": {"description": "The model"},
            "width": "${width}",
            "layers": [{"$class": "config_targets.Item", "$partial": True}],
            "loss": {"$symbol": "math.sqrt"},
        },
        "copy": "${model}",
        "stages": ({"epochs": 1}, {"epochs": 2}),
    }
    config = OmegaConf.create(content)
    validate(config)
    assert targets.CALLS == []
    assert config == content


def test_list_config():
    validate(OmegaConf.create([{"$class": "fractions.Fraction"}, 1]))
    with pytest.raises(TargetNotFoundError):
        validate(OmegaConf.create([{"$class": "fractions.NoSuchName"}]))


def test_part_of_a_config():
    config = OmegaConf.create(
        {
            "width": 3,
            "model": {"$class": "builtins.dict", "width": "${width}"},
            "other": {"$class": "fractions.NoSuchName"},
        }
    )
    validate(config.model)
    with pytest.raises(TargetNotFoundError):
        validate(config.other)


def test_read_only_config_is_accepted():
    config = OmegaConf.create(
        {"model": {"$class": "builtins.dict", "n": "${k}"}, "k": 3}
    )
    OmegaConf.set_readonly(config, True)
    validate(config)


@pytest.mark.parametrize(
    ("value", "error_type"),
    [
        ("???", ValidationMissingValueError),
        ("${nowhere}", ValidationInterpolationError),
    ],
)
def test_value_that_cannot_be_read_is_rejected(value: str, error_type: type[Exception]):
    for content, full_key in (
        ({"lr": value}, "lr"),
        ({"model": {"layers": [{"width": value}]}}, "model.layers[0].width"),
        ({"model": {"$class": "builtins.dict", "lr": value}}, "model.lr"),
        ({"stages": [1, value]}, "stages[1]"),
    ):
        config = OmegaConf.create(content)
        with pytest.raises(error_type) as error_info:
            validate(config)
        assert f"`{full_key}`" in _report(error_info.value)


def test_missing_root_is_rejected():
    with pytest.raises(ValidationMissingValueError):
        validate(DictConfig("???"))


@pytest.mark.parametrize(
    ("node", "error_type"),
    [
        ({"$class": "config_targets.NoSuchName"}, TargetNotFoundError),
        ({"$class": "???"}, ClassMissingValueError),
        ({"$class": "builtins.dict", "$partial": "yes"}, ClassTypeError),
        ({"$class": "builtins.dict", "$foo": 1}, ClassSyntaxError),
        ({"$symbol": "config_targets.NoSuchName"}, TargetNotFoundError),
        ({"$symbol": "math.sqrt", "reduction": "mean"}, SymbolSyntaxError),
    ],
)
def test_error_of_a_class_or_symbol_names_its_node(
    targets: ModuleType, node: dict[str, Any], error_type: type[Exception]
):
    config = OmegaConf.create({"models": [{"$class": "config_targets.Item"}, node]})
    with pytest.raises(error_type) as error_info:
        validate(config)
    assert error_info.value.__notes__ == ["  at `models[1]`"]
    assert targets.CALLS == []


@pytest.mark.parametrize("key", ["$partial", "$base", "$clas"])
def test_reserved_key_in_a_plain_mapping_is_rejected(key: str):
    config = OmegaConf.create({"model": {key: True, "width": 3}})
    with pytest.raises(ValidationSyntaxError, match=rf"\{key}") as error_info:
        validate(config)
    assert error_info.value.__notes__ == ["  at `model`"]


@pytest.mark.parametrize("meta", ["???", "${nowhere}", {"$foo": 1}])
def test_meta_is_not_read(meta: Any):
    validate(OmegaConf.create({"$meta": meta, "model": {"$meta": meta, "width": 3}}))


@pytest.mark.parametrize(
    ("content", "cycle"),
    [
        (
            {
                "a": {"$class": "builtins.dict", "other": "${b}"},
                "b": {"$class": "builtins.dict", "other": "${a}"},
            },
            "`a` -> `b` -> `a`",
        ),
        (
            {"model": {"parts": "${parts}"}, "parts": [{"model": "${model}"}]},
            "`model` -> `parts` -> `parts[0]` -> `model`",
        ),
    ],
)
def test_config_that_contains_itself_is_rejected(content: dict[str, Any], cycle: str):
    config = OmegaConf.create(content)
    with pytest.raises(ValidationCycleError) as error_info:
        validate(config)
    assert cycle in str(error_info.value)


def test_node_that_is_read_several_times_is_no_cycle():
    config = OmegaConf.create(
        {
            "encoder": {"$class": "builtins.dict", "width": 3},
            "first": {"encoder": "${encoder}", "inner": {"encoder": "${encoder}"}},
            "second": ["${encoder}", "${first}"],
        }
    )
    validate(config)


def _make_experiment(**values: Any) -> DictConfig:
    model = {"$class": "config_targets.Model", "depth": 2}
    return OmegaConf.create({"experiment": {"model": model, **values}}).experiment


def test_accepts_a_config_that_matches_its_schemas(targets: ModuleType):
    content = {
        "width": "3",
        "experiment": {
            "$class": "config_targets.Experiment",
            "$meta": {"description": "The baseline"},
            "seed": "${width}",
            "model": {
                "$class": "config_targets.Model",
                "depth": "${width}",
                "encoder": {"$class": "config_targets.SmallItem"},
            },
            "optimizer": {"$meta": {"note": "tuned"}, "lr": "1e-3", "mode": "SLOW"},
            "items": [
                {"$class": "config_targets.Item"},
                {"$symbol": "config_targets.ITEM"},
            ],
            "named_items": {"first": {"$class": "config_targets.make_item"}},
            "stages": [{"lr": 0.1}, "${experiment.optimizer}"],
            "schedule": {"$class": "config_targets.Item", "$partial": True},
            "extra": {"anything": [{"$class": "config_targets.Item"}]},
        },
    }
    config = OmegaConf.create(content)
    OmegaConf.set_readonly(config, True)
    validate(config)
    validate(config.experiment, targets.Experiment)
    assert targets.CALLS == []
    assert config == content


@pytest.mark.parametrize(
    ("values", "error_type", "full_key"),
    [
        ({"sed": 1}, SchemaKeyError, "experiment"),
        ({"seed": "many"}, SchemaValueError, "experiment"),
        ({"seed": "???"}, ValidationMissingValueError, "experiment.seed"),
        ({"optimizer": {}}, SchemaMissingValueError, "experiment.optimizer"),
        ({"optimizer": {"lr": 1, "total": 2}}, SchemaKeyError, "experiment.optimizer"),
        (
            {"optimizer": {"lr": 1, "betas": [1]}},
            SchemaValueError,
            "experiment.optimizer",
        ),
        (
            {"optimizer": {"lr": "???"}},
            ValidationMissingValueError,
            "experiment.optimizer.lr",
        ),
        (
            {"optimizer": {"lr": 1, "betas": [1, "???"]}},
            ValidationMissingValueError,
            "experiment.optimizer.betas[1]",
        ),
        (
            {"stages": [{"lr": 1}, {"lr": "x"}]},
            SchemaValueError,
            "experiment.stages[1]",
        ),
    ],
)
def test_value_that_does_not_match_its_schema_is_rejected(
    targets: ModuleType,
    values: dict[str, Any],
    error_type: type[Exception],
    full_key: str,
):
    with pytest.raises(error_type) as error_info:
        validate(_make_experiment(**values), targets.Experiment)
    assert f"`{full_key}`" in _report(error_info.value)
    assert targets.CALLS == []


def test_interpolated_value_is_checked_as_its_field(targets: ModuleType):
    config = OmegaConf.create({"seed": "many", "experiment": {"seed": "${seed}"}})
    config.experiment.model = {"$class": "config_targets.Model", "depth": 1}
    with pytest.raises(SchemaValueError, match="seed"):
        validate(config.experiment, targets.Experiment)


@pytest.mark.parametrize(
    ("values", "full_key"),
    [
        ({"model": {"$class": "config_targets.Item"}}, "experiment.model"),
        ({"model": None}, "experiment.model"),
        ({"model": {"depth": 2}}, "experiment.model"),
        ({"model": {"$symbol": "config_targets.SETTINGS"}}, "experiment.model"),
        (
            {"items": [{"$class": "config_targets.Model", "depth": 1}]},
            "experiment.items[0]",
        ),
        ({"items": {"first": {"$class": "config_targets.Item"}}}, "experiment.items"),
        ({"named_items": {"first": 3}}, "experiment.named_items.first"),
        ({"optimizer": {"$class": "config_targets.Item"}}, "experiment.optimizer"),
        ({"optimizer": None}, "experiment.optimizer"),
        ({"optimizer": [1, 2]}, "experiment.optimizer"),
    ],
)
def test_object_of_another_class_is_rejected(
    targets: ModuleType, values: dict[str, Any], full_key: str
):
    with pytest.raises(SchemaTypeError) as error_info:
        validate(_make_experiment(**values), targets.Experiment)
    assert error_info.value.__notes__ == [f"  at `{full_key}`"]
    assert targets.CALLS == []


@pytest.mark.parametrize(
    "optimizer",
    [
        {"$class": "config_targets.Optimizer", "lr": 1},
        {"$class": "config_targets.FastOptimizer", "lr": 1},
    ],
)
def test_class_in_a_dataclass_field_names_the_dataclass_or_a_subclass(
    targets: ModuleType, optimizer: dict[str, Any]
):
    validate(_make_experiment(optimizer=optimizer), targets.Experiment)


def test_class_in_a_dataclass_field_may_use_the_dataclass_as_its_schema(
    targets: ModuleType,
):
    backbone = {"$class": "config_targets.Model", "depth": "2"}
    validate(_make_experiment(backbone=backbone), targets.Experiment)
    validate(OmegaConf.create(backbone), targets.ModelConfig)
    for values, error_type in (
        ({"$class": "config_targets.Model", "depth": "deep"}, SchemaValueError),
        ({"$class": "config_targets.Model", "width": 2}, SchemaKeyError),
        ({"$class": "config_targets.Optimizer", "lr": 1}, SchemaTypeError),
        ({"$class": "config_targets.Item", "depth": 2}, SchemaTypeError),
    ):
        with pytest.raises(error_type) as error_info:
            validate(_make_experiment(backbone=values), targets.Experiment)
        assert error_info.value.__notes__ == ["  at `experiment.backbone`"]
    # `Settings` is a parent of the schema, but the class does not build one
    with pytest.raises(SchemaTypeError):
        validate(_make_experiment(settings=backbone), targets.Experiment)
    assert targets.CALLS == []


def test_schema_says_what_the_root_builds(targets: ModuleType):
    validate(OmegaConf.create({"lr": 1}), targets.Optimizer)
    fast_optimizer = {"$class": "config_targets.FastOptimizer", "lr": 1}
    validate(OmegaConf.create(fast_optimizer), targets.Optimizer)
    validate(OmegaConf.create({"$class": "config_targets.SmallItem"}), targets.Item)
    for content, schema in (
        ({"$class": "config_targets.Item"}, targets.Optimizer),
        ({"depth": 1}, targets.Model),
        ([{"lr": 1}], targets.Optimizer),
    ):
        with pytest.raises(SchemaTypeError) as error_info:
            validate(OmegaConf.create(content), schema)
        assert error_info.value.__notes__ == ["  at the root"]


def test_annotation_that_cannot_be_checked_takes_any_object():
    validate(OmegaConf.create({"greeter": {"$class": "fractions.Fraction"}}), _Parts)
    validate(OmegaConf.create({"greeter": {"$symbol": "math.pi"}}), _Parts)


@pytest.mark.parametrize(
    ("values", "is_valid"),
    [
        ({"alias": {"$class": "builtins.dict"}}, True),
        ({"alias": {"$class": "builtins.list"}}, False),
        ({"factory": {"$class": "fractions.Fraction", "$partial": True}}, True),
        ({"factory": {"$symbol": "math.sqrt"}}, True),
        ({"factory": {"$class": "fractions.Fraction"}}, False),
        ({"alias": {"$class": "builtins.dict", "$partial": True}}, False),
        ({"plain": {"$class": "builtins.list", "$partial": True}}, False),
        ({"kind": {"$symbol": "builtins.bool"}}, True),
        ({"kind": {"$class": "builtins.bool"}}, False),
        ({"plain": [{"$class": "fractions.Fraction"}]}, True),
        ({"plain": {"first": 1}}, False),
        ({"plain": (1, 2)}, False),
    ],
)
def test_annotation_is_checked_as_its_class(values: dict[str, Any], is_valid: bool):
    config = OmegaConf.create(values)
    if is_valid:
        validate(config, _Parts)
        return
    with pytest.raises(SchemaTypeError) as error_info:
        validate(config, _Parts)
    assert error_info.value.__notes__ == [f"  at `{next(iter(values))}`"]


def test_mapping_for_a_list_of_objects_names_the_field(targets: ModuleType):
    for values in ({"items": {"first": 1}}, {"stages": {"lr": 1}}):
        with pytest.raises(SchemaTypeError, match="a mapping") as error_info:
            validate(_make_experiment(**values), targets.Experiment)
        assert error_info.value.__notes__ == [f"  at `experiment.{next(iter(values))}`"]


def test_data_that_contains_itself_is_rejected():
    config = OmegaConf.create(
        {
            "first": {"other": "${second}"},
            "second": {"other": "${first}"},
            "parts": {"options": "${first}"},
        }
    )
    with pytest.raises(ValidationCycleError, match="`first` -> `second` -> `first`"):
        validate(config.parts, _Parts)


@pytest.mark.parametrize(
    ("options", "error_type"),
    [
        ({"$meta": {"note": "tuned"}, "first": {"a": "1"}}, None),
        ({"first": {"$meta": "???", "a": 1}}, None),
        ({"first": {"a": {"$symbol": "math.inf"}}}, SchemaValueError),
        ({"first": {"$foo": 1}}, ValidationSyntaxError),
        ({"first": {"$class": "builtins.dict"}}, SchemaTypeError),
        ({"first": {"a": {"$class": "builtins.int"}}}, SchemaTypeError),
    ],
)
def test_reserved_keys_keep_their_meaning_in_plain_values(
    options: dict[str, Any], error_type: type[Exception] | None
):
    config = OmegaConf.create({"options": options})
    if error_type is None:
        validate(config, _Parts)
        return
    with pytest.raises(error_type):
        validate(config, _Parts)


@pytest.mark.parametrize("schema", ["builtins.dict", _Parts()])
def test_schema_that_is_not_a_class_is_rejected(schema: Any):
    with pytest.raises(SchemaDefinitionError, match="must be a class"):
        validate(OmegaConf.create({}), schema)


def test_class_without_schema_takes_any_arguments(targets: ModuleType):
    validate(OmegaConf.create({"$class": "config_targets.Item", "seed": "many"}))


def test_schema_that_cannot_be_read_names_the_node(targets: ModuleType):
    config = OmegaConf.create({"model": {"$class": "config_targets.BrokenModel"}})
    with pytest.raises(SchemaDefinitionError) as error_info:
        validate(config)
    assert error_info.value.__notes__ == ["  at `model`"]


@pytest.mark.parametrize(
    ("error_type", "parent_type"),
    [
        (ValidationSyntaxError, ValueError),
        (ValidationInterpolationError, InterpolationResolutionError),
        (ValidationMissingValueError, MissingMandatoryValue),
        (ValidationCycleError, OmegaKitBaseException),
    ],
)
def test_errors_are_also_builtin_or_omegaconf_errors(
    error_type: type[Exception], parent_type: type[Exception]
):
    assert issubclass(error_type, ConfigValidationError)
    assert issubclass(error_type, OmegaKitBaseException)
    assert issubclass(error_type, parent_type)
