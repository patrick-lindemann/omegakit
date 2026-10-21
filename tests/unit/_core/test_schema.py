import enum
import fractions
import re
import sys
import typing
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Annotated, Any, Literal, Protocol, TypedDict, TypeVar

import pytest
import typing_extensions
from omegaconf import DictConfig, OmegaConf
from typing_extensions import NotRequired, Required, TypeAliasType

from omegakit._core.errors import (
    ConfigSchemaError,
    ConfigSymbolError,
    ConfigTargetError,
    ConfigValidationError,
    QualifiedNameNotFoundError,
    SchemaDefinitionError,
    ValidationInterpolationError,
    ValidationMissingValueError,
)
from omegakit._core.schema import is_valid, validate


class _Greeter(Protocol):
    name: str


_Mapping = TypeAliasType("_Mapping", dict[str, Any] | None)


class _Parts(TypedDict, total=False):
    greeter: _Greeter | None
    alias: _Mapping
    factory: Callable[..., Any] | None
    kind: type[int] | None
    any_kind: type[fractions.Fraction] | type
    plain: list | None
    options: dict[str, dict[str, int]] | None
    scale: float | fractions.Fraction


_OPTIMIZER = {"$target": "tests.targets.Optimizer"}


class _Mode(enum.Enum):
    FAST = 1
    EXACT = 2


class _Keyed(TypedDict, total=False):
    by_mode: dict[_Mode, fractions.Fraction]
    by_number: dict[int, fractions.Fraction]
    by_literal: dict[Literal["a", "b"], fractions.Fraction]
    by_union: dict[str | int, fractions.Fraction]


def test_accepts_a_valid_config_and_calls_nothing(targets: ModuleType):
    content = {
        "width": 3,
        "model": {
            "$target": "tests.targets.Item",
            "$meta": {"description": "The model"},
            "width": "${width}",
            "layers": [{"$target": "tests.targets.Item", "$partial": True}],
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
    validate(OmegaConf.create([{"$target": "fractions.Fraction"}, 1]))
    with pytest.raises(QualifiedNameNotFoundError):
        validate(OmegaConf.create([{"$target": "fractions.NoSuchName"}]))


def test_part_of_a_config():
    config = OmegaConf.create(
        {
            "width": 3,
            "model": {"$target": "builtins.dict", "width": "${width}"},
            "other": {"$target": "fractions.NoSuchName"},
        }
    )
    validate(config.model)
    with pytest.raises(QualifiedNameNotFoundError):
        validate(config.other)


def test_read_only_config_is_accepted():
    config = OmegaConf.create(
        {"model": {"$target": "builtins.dict", "n": "${k}"}, "k": 3}
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
@pytest.mark.parametrize(
    ("text", "full_key"),
    [
        ("lr: 'VALUE'", "lr"),
        ("model: {layers: [{width: 'VALUE'}]}", "model.layers[0].width"),
        ("model: {$target: builtins.dict, lr: 'VALUE'}", "model.lr"),
        ("stages: [1, 'VALUE']", "stages[1]"),
    ],
)
def test_value_that_cannot_be_read_is_rejected(
    value: str, error_type: type[Exception], text: str, full_key: str
):
    config = OmegaConf.create(text.replace("VALUE", value))
    with pytest.raises(error_type) as error_info:
        validate(config)
    error_info.match(re.escape(f"`{full_key}`"))


def test_missing_root_is_rejected():
    with pytest.raises(ValidationMissingValueError):
        validate(DictConfig("???"))
    validate(DictConfig("???"), allow_missing=True)


@pytest.mark.parametrize("value", ["???", "${nowhere}", "${unset}", "x${unset}"])
@pytest.mark.parametrize(
    "text",
    [
        "lr: 'VALUE'",
        "model: {layers: [{width: 'VALUE'}]}",
        "model: {$target: builtins.dict, lr: 'VALUE'}",
        "model: {$target: math.sqrt, $args: ['VALUE']}",
        "stages: [1, 'VALUE']",
    ],
)
def test_allow_missing_accepts_a_missing_value(value: str, text: str):
    config = OmegaConf.create(f"unset: ???\n{text.replace('VALUE', value)}")
    assert not is_valid(config)
    validate(config, allow_missing=True)
    assert is_valid(config, allow_missing=True)


@pytest.mark.parametrize(
    "values",
    [
        {"seed": "???"},
        {"seed": "${unset}"},
        {"model": "???"},
        {"optimizer": _OPTIMIZER},
        {"optimizer": {**_OPTIMIZER, "lr": "???", "steps": "${unset}"}},
        {"optimizer": {**_OPTIMIZER, "lr": 1, "betas": [1, "???"]}},
        {"pair": [{"$target": "tests.targets.Item"}, "???"]},
        {"backbone": {"activation": "relu"}},
    ],
)
def test_allow_missing_accepts_what_a_schema_requires(
    targets: ModuleType, values: dict[str, Any]
):
    experiment = _make_experiment(**values)
    with pytest.raises(ConfigValidationError):
        validate(experiment, targets.Experiment)
    validate(experiment, targets.Experiment, allow_missing=True)
    assert targets.CALLS == []


@pytest.mark.parametrize(
    ("values", "error_type", "full_key"),
    [
        ({"seed": "many"}, ConfigSchemaError, "experiment.seed"),
        (
            {"optimizer": {**_OPTIMIZER, "lr": "???", "steps": "many"}},
            ConfigSchemaError,
            "experiment.optimizer.steps",
        ),
        (
            {"optimizer": {**_OPTIMIZER, "lr": 1, "betas": [1, "x"], "steps": "???"}},
            ConfigSchemaError,
            "experiment.optimizer.betas",
        ),
        (
            {"pair": [{"$target": "tests.targets.Item"}, "x"]},
            ConfigSchemaError,
            "experiment.pair[1]",
        ),
        ({"sed": "???"}, ConfigSchemaError, "experiment"),
        ({"seed": "${nope:1}"}, ValidationInterpolationError, "experiment.seed"),
        (
            {"optimizer": {"$target": "???", "lr": 1}},
            ValidationMissingValueError,
            "experiment.optimizer.$target",
        ),
    ],
)
def test_allow_missing_still_checks_the_given_values(
    targets: ModuleType,
    values: dict[str, Any],
    error_type: type[Exception],
    full_key: str,
):
    with pytest.raises(error_type) as error_info:
        validate(_make_experiment(**values), targets.Experiment, allow_missing=True)
    error_info.match(re.escape(f"`{full_key}`"))


@pytest.mark.parametrize(
    ("node", "error_type"),
    [
        ({"$target": "tests.targets.NoSuchName"}, QualifiedNameNotFoundError),
        ({"$target": "???"}, ValidationMissingValueError),
        ({"$target": "builtins.dict", "$partial": "yes"}, ConfigTargetError),
        ({"$target": "builtins.dict", "$foo": 1}, ConfigValidationError),
        ({"$symbol": "tests.targets.NoSuchName"}, QualifiedNameNotFoundError),
        ({"$symbol": "math.sqrt", "reduction": "mean"}, ConfigSymbolError),
    ],
)
def test_error_of_a_target_or_symbol_names_its_node(
    targets: ModuleType, node: dict[str, Any], error_type: type[Exception]
):
    config = OmegaConf.create({"models": [{"$target": "tests.targets.Item"}, node]})
    with pytest.raises(error_type) as error_info:
        validate(config)
    error_info.match(re.escape("at `models[1]"))
    assert targets.CALLS == []


@pytest.mark.parametrize(
    ("node", "error_type", "full_key"),
    [
        ({"$target": "math.sqrt", "$args": 2}, ConfigTargetError, "models[1]"),
        ({"$target": "math.sqrt", "$args": {"x": 2}}, ConfigTargetError, "models[1]"),
        (
            {"$target": "math.sqrt", "$args": ["???"]},
            ValidationMissingValueError,
            "models[1].$args[0]",
        ),
        (
            {"$target": "builtins.list", "$args": [[{"$target": "math.nope"}]]},
            QualifiedNameNotFoundError,
            "models[1].$args[0][0]",
        ),
        (
            {"$target": "tests.targets.Configured", "$args": [1]},
            ConfigTargetError,
            "models[1]",
        ),
        (
            {"$target": "tests.targets.Model", "$args": [1]},
            ConfigTargetError,
            "models[1]",
        ),
        (
            {"$target": "tests.targets.Layer", "$args": [1]},
            ConfigTargetError,
            "models[1]",
        ),
        ({"$args": [1]}, ConfigValidationError, "models[1]"),
        ({"$symbol": "math.pi", "$args": [1]}, ConfigSymbolError, "models[1]"),
    ],
)
def test_args_that_cannot_be_passed_are_rejected(
    targets: ModuleType,
    node: dict[str, Any],
    error_type: type[Exception],
    full_key: str,
):
    config = OmegaConf.create({"models": [{"$target": "tests.targets.Item"}, node]})
    with pytest.raises(error_type) as error_info:
        validate(config)
    error_info.match(re.escape(f"at `{full_key}`"))
    assert targets.CALLS == []


@pytest.mark.parametrize("key", ["$partial", "$base", "$clas"])
def test_reserved_key_in_a_plain_mapping_is_rejected(key: str):
    config = OmegaConf.create({"model": {key: True, "width": 3}})
    with pytest.raises(ConfigValidationError, match=rf"\{key}") as error_info:
        validate(config)
    error_info.match(re.escape("at `model`"))


@pytest.mark.parametrize("meta", ["???", "${nowhere}", {"$foo": 1}])
def test_meta_is_not_read(meta: Any):
    validate(OmegaConf.create({"$meta": meta, "model": {"$meta": meta, "width": 3}}))


@pytest.mark.parametrize(
    ("content", "cycle"),
    [
        (
            {
                "a": {"$target": "builtins.dict", "other": "${b}"},
                "b": {"$target": "builtins.dict", "other": "${a}"},
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
    with pytest.raises(ConfigValidationError) as error_info:
        validate(config)
    assert cycle in str(error_info.value)


def test_node_that_is_read_several_times_is_no_cycle():
    config = OmegaConf.create(
        {
            "encoder": {"$target": "builtins.dict", "width": 3},
            "first": {"encoder": "${encoder}", "inner": {"encoder": "${encoder}"}},
            "second": ["${encoder}", "${first}"],
        }
    )
    validate(config)


def _make_experiment(**values: Any) -> DictConfig:
    model = {"$target": "tests.targets.Model", "depth": 2}
    experiment = {"$target": "tests.targets.Experiment", "model": model, **values}
    # `unset` is a missing value for interpolations to point to
    return OmegaConf.create({"experiment": experiment, "unset": "???"}).experiment


def test_accepts_a_config_that_matches_its_schemas(targets: ModuleType):
    content = {
        "width": "3",
        "experiment": {
            "$target": "tests.targets.Experiment",
            "$meta": {"description": "The baseline"},
            "seed": "${width}",
            "model": {
                "$target": "tests.targets.Model",
                "depth": "${width}",
                "encoder": {"$target": "tests.targets.SmallItem"},
            },
            "optimizer": {
                "$target": "tests.targets.Optimizer",
                "$meta": {"note": "tuned"},
                "lr": "1e-3",
                "mode": "SLOW",
            },
            "items": [
                {"$target": "tests.targets.Item"},
                {"$symbol": "tests.targets.ITEM"},
            ],
            "named_items": {"first": {"$target": "tests.targets.make_item"}},
            "stages": [
                {"$target": "tests.targets.FastOptimizer", "lr": 0.1},
                "${experiment.optimizer}",
            ],
            "schedules": {"warmup": "${experiment.optimizer}"},
            "schedule": {"$target": "tests.targets.Item", "$partial": True},
            "extra": {"anything": [{"$target": "tests.targets.Item"}]},
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
        ({"sed": 1}, ConfigSchemaError, "experiment"),
        ({"seed": "many"}, ConfigSchemaError, "experiment.seed"),
        ({"seed": "???"}, ValidationMissingValueError, "experiment.seed"),
        ({"optimizer": {**_OPTIMIZER}}, ConfigSchemaError, "experiment.optimizer"),
        (
            {"optimizer": {**_OPTIMIZER, "lr": 1, "total": 2}},
            ConfigSchemaError,
            "experiment.optimizer",
        ),
        (
            {"optimizer": {**_OPTIMIZER, "lr": 1, "betas": [1]}},
            ConfigSchemaError,
            "experiment.optimizer.betas",
        ),
        (
            {"optimizer": {**_OPTIMIZER, "lr": "???"}},
            ValidationMissingValueError,
            "experiment.optimizer.lr",
        ),
        (
            {"optimizer": {**_OPTIMIZER, "lr": 1, "betas": [1, "???"]}},
            ValidationMissingValueError,
            "experiment.optimizer.betas[1]",
        ),
        (
            {"stages": [{**_OPTIMIZER, "lr": 1}, {**_OPTIMIZER, "lr": "x"}]},
            ConfigSchemaError,
            "experiment.stages[1].lr",
        ),
        (
            {"schedules": {"warmup": {**_OPTIMIZER, "steps": 2}}},
            ConfigSchemaError,
            "experiment.schedules.warmup",
        ),
        (
            {"pair": [{"$target": "tests.targets.Item"}, "x"]},
            ConfigSchemaError,
            "experiment.pair[1]",
        ),
        (
            {"pair": [{"$target": "tests.targets.Item"}]},
            ConfigSchemaError,
            "experiment.pair",
        ),
        (
            {"pair": [{"$target": "tests.targets.Model", "depth": 1}, 0.5]},
            ConfigSchemaError,
            "experiment.pair[0]",
        ),
        (
            {"phases": [{"depth": 1}, {"depht": 2}]},
            ConfigSchemaError,
            "experiment.phases[1]",
        ),
        (
            {"named_items": {1: {"$target": "tests.targets.Item"}}},
            ConfigSchemaError,
            "experiment.named_items",
        ),
        (
            {"backbone": {"$symbol": "tests.targets.SETTINGS"}},
            ConfigSchemaError,
            "experiment.backbone",
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
    error_info.match(re.escape(f"`{full_key}`"))
    assert targets.CALLS == []


def test_interpolated_value_is_checked_as_its_field(targets: ModuleType):
    experiment = {"$target": "tests.targets.Experiment", "seed": "${seed}"}
    config = OmegaConf.create({"seed": "many", "experiment": experiment})
    config.experiment.model = {"$target": "tests.targets.Model", "depth": 1}
    with pytest.raises(ConfigSchemaError, match="seed"):
        validate(config.experiment, targets.Experiment)


@pytest.mark.parametrize(
    ("values", "full_key"),
    [
        ({"model": {"$target": "tests.targets.Item"}}, "experiment.model"),
        ({"model": None}, "experiment.model"),
        ({"model": {"depth": 2}}, "experiment.model"),
        ({"model": {"$symbol": "tests.targets.SETTINGS"}}, "experiment.model"),
        (
            {"items": [{"$target": "tests.targets.Model", "depth": 1}]},
            "experiment.items[0]",
        ),
        ({"items": {"first": {"$target": "tests.targets.Item"}}}, "experiment.items"),
        ({"named_items": {"first": 3}}, "experiment.named_items.first"),
        ({"optimizer": {"$target": "tests.targets.Item"}}, "experiment.optimizer"),
        ({"optimizer": None}, "experiment.optimizer"),
        ({"optimizer": [1, 2]}, "experiment.optimizer"),
        ({"optimizer": {"lr": 1}}, "experiment.optimizer"),
        ({"stages": [{"lr": 1}]}, "experiment.stages[0]"),
        ({"schedules": {"warmup": {"lr": 1}}}, "experiment.schedules.warmup"),
    ],
)
def test_object_of_another_class_is_rejected(
    targets: ModuleType, values: dict[str, Any], full_key: str
):
    with pytest.raises(ConfigSchemaError) as error_info:
        validate(_make_experiment(**values), targets.Experiment)
    error_info.match(re.escape(f"at `{full_key}`"))
    assert targets.CALLS == []


@pytest.mark.parametrize(
    "optimizer",
    [
        {"$target": "tests.targets.Optimizer", "lr": 1},
        {"$target": "tests.targets.FastOptimizer", "lr": 1},
    ],
)
def test_class_in_a_dataclass_field_names_the_dataclass_or_a_subclass(
    targets: ModuleType, optimizer: dict[str, Any]
):
    validate(_make_experiment(optimizer=optimizer), targets.Experiment)


def test_field_that_is_annotated_with_a_schema_takes_a_mapping(targets: ModuleType):
    backbone = {"depth": "2", "encoder": {"$target": "tests.targets.Item"}}
    validate(_make_experiment(backbone=backbone), targets.Experiment)
    validate(_make_experiment(backbone=None), targets.Experiment)
    validate(OmegaConf.create(backbone), targets.ModelConfig)
    model = OmegaConf.create({"$target": "tests.targets.Model", "depth": 2})
    with pytest.raises(ConfigSchemaError):
        validate(model, targets.ModelConfig)
    assert targets.CALLS == []


@pytest.mark.parametrize(
    ("backbone", "full_key"),
    [
        ({"depth": "deep"}, "experiment.backbone.depth"),
        ({"depth": 2, "width": 2}, "experiment.backbone"),
        ({"activation": "tanh"}, "experiment.backbone"),
        ({"$target": "tests.targets.Model", "depth": 2}, "experiment.backbone"),
        ({"$target": "tests.targets.ModelConfig", "depth": 2}, "experiment.backbone"),
        ({"$symbol": "tests.targets.ITEM"}, "experiment.backbone"),
        ([1, 2], "experiment.backbone"),
    ],
)
def test_field_that_is_annotated_with_a_schema_rejects_what_is_no_such_mapping(
    targets: ModuleType, backbone: Any, full_key: str
):
    with pytest.raises(ConfigSchemaError) as error_info:
        validate(_make_experiment(backbone=backbone), targets.Experiment)
    error_info.match(re.escape(f"at `{full_key}`"))
    assert targets.CALLS == []


@pytest.mark.parametrize("schema", ["CollectionConfig", "BackportedCollectionConfig"])
def test_mapping_in_a_union_of_schemas_is_checked_against_the_one_it_fits(
    targets: ModuleType, schema: str
):
    sources = [
        {"type": "file", "path": "a.yaml", "filter": {"select": ["cube"]}},
        {"type": "file", "path": "b.yaml", "filter": {"match": "c.*"}},
        {"type": "file", "path": "c.yaml"},
        {"type": "directory", "path": "c", "depth": "2"},
        {"url": "https://example.com"},
        {"$symbol": "tests.targets.URL_SOURCE"},
    ]
    validate(OmegaConf.create({"sources": sources}), getattr(targets, schema))


@pytest.mark.parametrize("schema", ["CollectionConfig", "BackportedCollectionConfig"])
@pytest.mark.parametrize(
    ("source", "full_key", "message"),
    [
        (
            {"type": "file", "path": "a.yaml", "depth": 2},
            "sources[0]",
            "The mapping fits none of `FileSourceConfig`, `DirectorySourceConfig`, "
            "`UrlSourceConfig`: `depth` is not a field of `FileSourceConfig`; "
            "`DirectorySourceConfig.type` takes `'directory'`; `type`, `path`, "
            "`depth` is not a field of `UrlSourceConfig`.",
        ),
        ({"type": "link", "path": "a"}, "sources[0]", "`FileSourceConfig.type` takes"),
        (
            {"type": "directory"},
            "sources[0]",
            "`DirectorySourceConfig` requires `path`",
        ),
        ({"retries": 2}, "sources[0]", "`UrlSourceConfig` requires `url`"),
        (
            {"type": "directory", "path": "a", "depth": "deep"},
            "sources[0].depth",
            "does not match `DirectorySourceConfig`",
        ),
        (
            {"type": "file", "path": "a", "filter": {"pattern": "c.*"}},
            "sources[0].filter",
            "fits none of `SelectFilterConfig`, `MatchFilterConfig`",
        ),
        (
            {"type": "file", "path": "a", "filter": {"select": "cube"}},
            "sources[0].filter.select",
            "does not match `SelectFilterConfig`",
        ),
    ],
)
def test_mapping_that_fits_no_schema_of_a_union_is_rejected(
    targets: ModuleType,
    schema: str,
    source: dict[str, Any],
    full_key: str,
    message: str,
):
    config = OmegaConf.create({"sources": [source]})
    with pytest.raises(ConfigSchemaError) as error_info:
        validate(config, getattr(targets, schema))
    error_info.match(re.escape(message))
    error_info.match(re.escape(f"at `{full_key}`"))


def test_allow_missing_accepts_a_union_of_schemas_without_required_keys(
    targets: ModuleType,
):
    config = OmegaConf.create({"sources": [{"type": "directory"}]})
    validate(config, targets.CollectionConfig, allow_missing=True)


@pytest.mark.parametrize(
    ("make_annotation", "symbol", "wrong_symbol"),
    [
        (lambda item: list[item], "BACKBONES", "WRONG_BACKBONES"),
        (lambda item: dict[str, item], "NAMED_BACKBONES", "NAMED_WRONG_BACKBONES"),
        (lambda item: tuple[item, ...], "BACKBONE_PAIR", "WRONG_BACKBONE_PAIR"),
    ],
    ids=["list", "dict", "tuple"],
)
def test_symbol_of_a_container_is_checked_by_its_items(
    targets: ModuleType,
    make_annotation: Callable[[type], Any],
    symbol: str,
    wrong_symbol: str,
):
    annotation = make_annotation(targets.ModelConfig)
    _validate_value(annotation, {"$symbol": f"tests.targets.{symbol}"})
    with pytest.raises(ConfigSchemaError, match=r"ModelConfig.*at `value`"):
        _validate_value(annotation, {"$symbol": f"tests.targets.{wrong_symbol}"})


def test_symbol_of_a_list_of_objects_is_checked_by_its_items(targets: ModuleType):
    annotation = list[targets.Item] | None
    with pytest.raises(ConfigSchemaError, match=r"Expected `Item`.*at `value`"):
        _validate_value(annotation, {"$symbol": "tests.targets.NUMBERS"})


def test_symbol_of_another_container_is_rejected(targets: ModuleType):
    with pytest.raises(ConfigSchemaError, match=r"gives a tuple.*at `value`"):
        _validate_value(
            list[targets.ModelConfig], {"$symbol": "tests.targets.BACKBONE_PAIR"}
        )


@pytest.mark.parametrize("annotation", [list[Any], list, Any, object])
def test_symbol_of_items_that_are_not_checked_is_taken_as_it_is(annotation: Any):
    _validate_value(annotation, {"$symbol": "tests.targets.RAW_NODES"})


class _Square(TypedDict):
    kind: Literal["square"]
    side: int


class _Circle(TypedDict):
    kind: Literal["circle"]
    radius: int


T = TypeVar("T")
_Optional = TypeAliasType("_Optional", T | None, type_params=(T,))
_ListOf = TypeAliasType("_ListOf", list[T], type_params=(T,))
_AnnotatedSquare = TypeAliasType("_AnnotatedSquare", Annotated[_Square, "doc"])
_Shape = TypeAliasType("_Shape", Annotated[_Square, "doc"] | _Circle)
_SQUARE_FORMS: list[Any] = [
    _Optional[_Square],
    _AnnotatedSquare,
    Annotated[_Square, "doc"],
    _Optional[_Square | _Circle],
    _Shape,
]
_SQUARE_LIST_FORMS: list[Any] = [
    _ListOf[_Square],
    list[_AnnotatedSquare],
    _ListOf[_Optional[_Square]],
]
if sys.version_info >= (3, 12):
    # The aliases that a `type` statement makes
    _StatementSquare = typing.TypeAliasType(
        "_StatementSquare", Annotated[_Square, "doc"]
    )
    _StatementSquares = typing.TypeAliasType("_StatementSquares", list[_Square])
    _SQUARE_FORMS.append(_StatementSquare)
    _SQUARE_LIST_FORMS.append(_StatementSquares)


_SQUARE = {"kind": "square", "side": "2"}
_BAD_SQUARE = {"kind": "square", "side": 2, "typo": 1}


@pytest.mark.parametrize(
    ("annotation", "value", "bad_value", "full_key"),
    [
        (list[_Square] | int, [_SQUARE], [_BAD_SQUARE], "value[0]"),
        (dict[str, _Square] | int, {"a": _SQUARE}, {"a": _BAD_SQUARE}, "value.a"),
        (tuple[_Square, ...] | int, [_SQUARE], [_BAD_SQUARE], "value[0]"),
        (list[_Square] | _Square, [_SQUARE], [_BAD_SQUARE], "value[0]"),
        (list[_Square] | _Square, _SQUARE, _BAD_SQUARE, "value"),
        (list[_Circle | _Square] | None, [_SQUARE], [_BAD_SQUARE], "value[0]"),
    ],
)
def test_container_in_a_union_checks_its_items(
    annotation: Any, value: Any, bad_value: Any, full_key: str
):
    _validate_value(annotation, value)
    with pytest.raises(ConfigSchemaError, match=rf"`typo`.*at `{re.escape(full_key)}`"):
        _validate_value(annotation, bad_value)


@pytest.mark.parametrize(
    "annotation",
    [tuple[()], typing.Tuple[()], tuple[()] | _Square],  # noqa: UP006
)
def test_empty_tuple_takes_no_items(annotation: Any):
    _validate_value(annotation, [])
    with pytest.raises(ConfigSchemaError, match=r"length 2 .* 0|Expected 0 items"):
        _validate_value(annotation, [1, 2])


def test_container_in_a_union_takes_the_other_members():
    _validate_value(list[_Square] | int, 3)
    with pytest.raises(ConfigSchemaError, match="Expected"):
        _validate_value(list[_Square] | int, _SQUARE)


def test_list_in_a_union_with_its_item_class_checks_its_items(targets: ModuleType):
    annotation = list[targets.Item] | targets.Item
    _validate_value(annotation, [{"$target": "tests.targets.SmallItem"}])
    with pytest.raises(ConfigSchemaError, match=r"Expected `Item`.*at `value\[0\]`"):
        _validate_value(annotation, [1])


def test_mapping_that_fits_no_schema_is_checked_by_the_dict_of_its_union():
    annotation = _Square | dict[str, int]
    _validate_value(annotation, {"kind": "square", "side": "2"})
    _validate_value(annotation, {"width": 2})
    with pytest.raises(ConfigSchemaError, match=r"Expected `int`.*at `value.width`"):
        _validate_value(annotation, {"width": "wide"})


@pytest.mark.parametrize(
    ("annotation", "value"),
    [
        (list[_Square] | list[_Circle], [_SQUARE]),
        (dict[str, _Square] | dict[str, int], {"a": 1}),
    ],
)
def test_several_containers_of_one_kind_in_a_union_are_rejected(
    annotation: Any, value: Any
):
    with pytest.raises(SchemaDefinitionError, match=r"holds several.*at `value`"):
        _validate_value(annotation, value)


_SquareTag = TypeAliasType("_SquareTag", Literal["square"])


class _TaggedSquare(TypedDict):
    kind: _SquareTag
    side: int


class _TaggedRectangle(TypedDict):
    kind: Literal["rectangle"] | None
    side: int


class _One(TypedDict):
    value: Literal[1]


class _Flag(TypedDict):
    value: Literal[True]


@pytest.mark.parametrize(
    ("annotation", "value"),
    [
        (_TaggedSquare | _TaggedRectangle, {"kind": "rectangle", "side": 1}),
        (_TaggedSquare | _TaggedRectangle, {"kind": None, "side": 1}),
        (_TaggedRectangle | _TaggedSquare, {"kind": "square", "side": 1}),
        (_One | _Flag, {"value": True}),
        (_Flag | _One, {"value": 1}),
    ],
)
def test_tag_behind_an_alias_or_a_union_selects_its_schema(
    annotation: Any, value: dict[str, Any]
):
    _validate_value(annotation, value)


def test_value_that_matches_no_tag_names_the_tags():
    with pytest.raises(
        ConfigSchemaError,
        match=re.escape(
            "`_TaggedSquare.kind` takes `'square'`; `_TaggedRectangle.kind` takes "
            "`'rectangle'`, `None`."
        ),
    ):
        _validate_value(
            _TaggedSquare | _TaggedRectangle, {"kind": "triangle", "side": 1}
        )


class _Marks(TypedDict, total=False):
    width: Annotated[Required[int], "doc"]
    depth: int


class _BackportedMarks(typing_extensions.TypedDict, total=False):
    width: Annotated[Required[int], "doc"]
    depth: int


class _OptionalMarks(TypedDict):
    width: Annotated[NotRequired[int], "doc"]
    depth: int


class _BackportedOptionalMarks(typing_extensions.TypedDict):
    width: Annotated[NotRequired[int], "doc"]
    depth: int


@pytest.mark.parametrize(
    ("schema", "optional_schema"),
    [(_Marks, _OptionalMarks), (_BackportedMarks, _BackportedOptionalMarks)],
    ids=["typing", "typing_extensions"],
)
def test_mark_inside_annotated_decides_whether_a_key_is_required(
    schema: type, optional_schema: type
):
    config = OmegaConf.create({"depth": 1})
    validate(config, optional_schema)
    with pytest.raises(ConfigSchemaError, match="requires `width`"):
        validate(config, schema)


def _validate_value(annotation: Any, value: Any, **kwargs: Any) -> None:
    # The annotation is a parameter, which the class syntax cannot take
    holder = TypedDict("holder", {"value": annotation})  # noqa: UP013
    validate(OmegaConf.create({"value": value}), holder, **kwargs)


@pytest.mark.parametrize("annotation", _SQUARE_FORMS)
def test_schema_behind_an_alias_or_annotated_is_checked(annotation: Any):
    _validate_value(annotation, {"kind": "square", "side": "2"})
    with pytest.raises(ConfigSchemaError, match=r"`typo`.*at `value`"):
        _validate_value(annotation, {"kind": "square", "side": 2, "typo": 1})


@pytest.mark.parametrize("annotation", _SQUARE_LIST_FORMS)
def test_list_of_schemas_behind_an_alias_is_checked(annotation: Any):
    _validate_value(annotation, [{"kind": "square", "side": "2"}])
    with pytest.raises(ConfigSchemaError, match=r"`typo`.*at `value\[0\]`"):
        _validate_value(annotation, [{"kind": "square", "side": 2, "typo": 1}])


def test_result_of_a_function_is_not_known_before_it_is_called(targets: ModuleType):
    validate(_make_experiment(model={"$target": "tests.targets.make_item"}))
    assert targets.CALLS == []


def test_partial_may_leave_required_keys_open(targets: ModuleType):
    model = {"$target": "tests.targets.Model", "$partial": True}
    validate(OmegaConf.create({"models": [model, {**model, "activation": "tanh"}]}))
    with pytest.raises(ConfigSchemaError):
        validate(OmegaConf.create({**model, "$partial": False}))
    with pytest.raises(ConfigSchemaError):
        validate(OmegaConf.create({**model, "width": 3}))
    with pytest.raises(ConfigSchemaError):
        validate(OmegaConf.create({**model, "depth": "deep"}))


def test_schema_says_what_the_root_builds(targets: ModuleType):
    optimizer = {"$target": "tests.targets.Optimizer", "lr": 1}
    validate(OmegaConf.create(optimizer), targets.Optimizer)
    fast_optimizer = {"$target": "tests.targets.FastOptimizer", "lr": 1}
    validate(OmegaConf.create(fast_optimizer), targets.Optimizer)
    validate(OmegaConf.create({"$target": "tests.targets.SmallItem"}), targets.Item)


@pytest.mark.parametrize(
    ("content", "schema_name"),
    [
        ({"$target": "tests.targets.Item"}, "Optimizer"),
        ({"depth": 1}, "Model"),
        ({"lr": 1}, "Optimizer"),
        ([{"lr": 1}], "Optimizer"),
    ],
)
def test_root_that_builds_something_else_is_rejected(
    targets: ModuleType, content: Any, schema_name: str
):
    with pytest.raises(ConfigSchemaError) as error_info:
        validate(OmegaConf.create(content), getattr(targets, schema_name))
    error_info.match(re.escape("at the root"))


def test_annotation_that_cannot_be_checked_takes_any_object():
    validate(OmegaConf.create({"greeter": {"$target": "fractions.Fraction"}}), _Parts)
    validate(OmegaConf.create({"greeter": {"$symbol": "math.pi"}}), _Parts)


@pytest.mark.parametrize(
    ("values", "is_valid"),
    [
        ({"alias": {"$target": "builtins.dict"}}, True),
        ({"alias": {"$target": "builtins.list"}}, False),
        ({"factory": {"$target": "fractions.Fraction", "$partial": True}}, True),
        ({"factory": {"$symbol": "math.sqrt"}}, True),
        ({"factory": {"$target": "fractions.Fraction"}}, False),
        ({"alias": {"$target": "builtins.dict", "$partial": True}}, False),
        ({"plain": {"$target": "builtins.list", "$partial": True}}, False),
        ({"kind": {"$symbol": "builtins.bool"}}, True),
        ({"kind": {"$symbol": "builtins.str"}}, False),
        ({"kind": {"$target": "builtins.bool"}}, False),
        ({"any_kind": {"$symbol": "builtins.str"}}, True),
        ({"any_kind": {"$symbol": "fractions.Fraction"}}, True),
        ({"any_kind": {"$symbol": "math.pi"}}, False),
        ({"plain": [{"$target": "fractions.Fraction"}]}, True),
        ({"plain": {"first": 1}}, False),
        ({"plain": (1, 2)}, False),
        ({"scale": 0.5}, True),
        ({"scale": {"$target": "fractions.Fraction"}}, True),
        ({"scale": 1}, False),
        ({"scale": "3e-4"}, False),
    ],
)
def test_annotation_is_checked_as_its_class(values: dict[str, Any], is_valid: bool):
    config = OmegaConf.create(values)
    if is_valid:
        validate(config, _Parts)
        return
    with pytest.raises(ConfigSchemaError) as error_info:
        validate(config, _Parts)
    error_info.match(re.escape(f"at `{next(iter(values))}`"))


@pytest.mark.parametrize(
    ("field", "value"), [("items", {"first": 1}), ("stages", {"lr": 1})]
)
def test_mapping_for_a_list_of_objects_names_the_field(
    targets: ModuleType, field: str, value: dict[str, Any]
):
    with pytest.raises(ConfigSchemaError, match="a mapping") as error_info:
        validate(_make_experiment(**{field: value}), targets.Experiment)
    error_info.match(re.escape(f"at `experiment.{field}`"))


def test_data_that_contains_itself_is_rejected():
    config = OmegaConf.create(
        {
            "first": {"other": "${second}"},
            "second": {"other": "${first}"},
            "parts": {"options": "${first}"},
        }
    )
    with pytest.raises(ConfigValidationError, match="`first` -> `second` -> `first`"):
        validate(config.parts, _Parts)


@pytest.mark.parametrize(
    ("options", "error_type"),
    [
        ({"$meta": {"note": "tuned"}, "first": {"a": "1"}}, None),
        ({"first": {"$meta": "???", "a": 1}}, None),
        ({"first": {"a": {"$symbol": "math.inf"}}}, ConfigSchemaError),
        ({"first": {"$foo": 1}}, ConfigValidationError),
        ({"first": {"$target": "builtins.dict"}}, ConfigSchemaError),
        ({"first": {"a": {"$target": "builtins.int"}}}, ConfigSchemaError),
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


@pytest.mark.parametrize(
    "schema", ["builtins.dict", _Parts(), list[_Parts], dict[str, int], type[int]]
)
def test_schema_that_is_not_a_class_is_rejected(schema: Any):
    with pytest.raises(SchemaDefinitionError, match="must be a class"):
        validate(OmegaConf.create({}), schema)


def test_error_of_a_parametrized_class_names_its_arguments():
    with pytest.raises(ConfigSchemaError, match=r"Expected `type\[int\]`"):
        _validate_value(type[int], {"$symbol": "builtins.str"})


def test_class_without_schema_takes_any_arguments(targets: ModuleType):
    validate(OmegaConf.create({"$target": "tests.targets.Item", "seed": "many"}))


def test_schema_that_cannot_be_read_names_the_node(targets: ModuleType):
    config = OmegaConf.create({"model": {"$target": "tests.targets.BrokenModel"}})
    with pytest.raises(SchemaDefinitionError) as error_info:
        validate(config)
    error_info.match(re.escape("at `model`"))


@pytest.mark.parametrize("key", ["$target", "$symbol"])
def test_error_of_an_import_keeps_its_type_and_names_the_node(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, key: str
):
    (tmp_path / "failing_module.py").write_text("raise RuntimeError('no GPU')\n")
    monkeypatch.syspath_prepend(tmp_path)
    config = OmegaConf.create({"models": [{key: "failing_module.Model"}]})
    with pytest.raises(RuntimeError, match="no GPU") as error_info:
        validate(config)
    error_info.match(re.escape("`models[0]`"))


def test_plain_dict_is_checked_like_a_config(targets: ModuleType):
    validate({"model": {"$target": "tests.targets.Item", "name": "plain"}})
    with pytest.raises(ValidationMissingValueError) as error_info:
        validate({"model": {"depth": "???"}})
    error_info.match(re.escape("`model.depth`"))


@pytest.mark.parametrize(
    ("field", "key", "is_valid"),
    [
        ("by_mode", "FAST", True),
        ("by_mode", "SLOW", False),
        ("by_number", 3, True),
        ("by_number", "three", False),
    ],
)
def test_key_of_a_dictionary_of_objects_follows_its_annotation(
    field: str, key: Any, is_valid: bool
):
    config = OmegaConf.create({field: {key: {"$target": "fractions.Fraction"}}})
    if is_valid:
        validate(config, _Keyed)
        return
    with pytest.raises(ConfigSchemaError) as error_info:
        validate(config, _Keyed)
    error_info.match(re.escape(f"`{field}`"))


@pytest.mark.parametrize("field", ["by_literal", "by_union"])
def test_key_annotation_that_omegaconf_does_not_support_is_rejected(field: str):
    config = OmegaConf.create({field: {"a": {"$target": "fractions.Fraction"}}})
    with pytest.raises(SchemaDefinitionError) as error_info:
        validate(config, _Keyed)
    assert not isinstance(error_info.value, ConfigValidationError)


def test_unknown_key_names_the_fields_of_its_schema():
    config = OmegaConf.create({"scael": 0.5})
    with pytest.raises(ConfigSchemaError, match="scael") as error_info:
        validate(config, _Parts)
    error_info.match("`scale`")


def test_is_valid_accepts_a_valid_config(targets: ModuleType):
    assert is_valid({"$target": "tests.targets.Model", "depth": 2})
    assert is_valid({"depth": 2}, targets.ModelConfig)


@pytest.mark.parametrize(
    "content",
    [
        {"depth": "???"},
        {"depth": "deep"},
        {"depth": 2, "width": 3},
        {"model": {"$target": "tests.targets.Nope"}},
    ],
)
def test_is_valid_rejects_an_invalid_config(targets: ModuleType, content: dict):
    schema = None if "model" in content else targets.ModelConfig
    assert not is_valid(content, schema)


def test_is_valid_raises_for_a_broken_schema(targets: ModuleType):
    with pytest.raises(SchemaDefinitionError):
        is_valid({"model": {"$target": "tests.targets.BrokenModel"}})
