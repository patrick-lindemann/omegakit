import fractions
import functools
import pathlib
import re
from types import ModuleType
from typing import Any

import pytest
from omegaconf import OmegaConf

from omegakit._core.errors import (
    ConfigSchemaError,
    ConfigTargetError,
    ConfigValidationError,
    QualifiedNameNotFoundError,
    ValidationInterpolationError,
    ValidationMissingValueError,
)
from omegakit._core.features.target import make_node
from omegakit._core.instantiate import instantiate, prepare


def test_builds_the_object_of_a_class():
    content = {"$target": "fractions.Fraction", "numerator": 1, "denominator": "${two}"}
    config = OmegaConf.create({"half": content, "two": 2})
    OmegaConf.set_readonly(config, True)
    assert instantiate(config.half) == fractions.Fraction(1, 2)
    assert config == {"half": content, "two": 2}


def test_nested_classes_are_built_as_arguments(targets: ModuleType):
    config = OmegaConf.create(
        {
            "$target": "config_targets.Item",
            "inner": {"$target": "config_targets.Item", "name": "inner"},
            "items": [{"$target": "config_targets.Item", "name": "listed"}],
            "pair": ({"$target": "config_targets.Item", "name": "paired"}, 2),
            "plain": {"depth": {"width": 3}},
            "name": "outer",
        }
    )
    kwargs = instantiate(config).kwargs
    assert isinstance(kwargs["inner"], targets.Item)
    assert type(kwargs["items"]) is list
    assert isinstance(kwargs["items"][0], targets.Item)
    assert type(kwargs["pair"]) is tuple
    assert isinstance(kwargs["pair"][0], targets.Item)
    assert kwargs["plain"] == {"depth": {"width": 3}}
    assert type(kwargs["plain"]) is dict
    assert targets.CALLS == ["inner", "listed", "paired", "outer"]


@pytest.mark.parametrize("is_reversed", [False, True])
def test_every_read_of_a_class_builds_its_own_object(
    targets: ModuleType, is_reversed: bool
):
    content = {
        "model": {"$target": "config_targets.Item", "name": "model"},
        "trainer": {"$target": "config_targets.Item", "model": "${model}"},
        "tester": {"models": [{"model": "${model}"}]},
        "same": "${model}",
    }
    if is_reversed:
        content = dict(reversed(content.items()))
    config = OmegaConf.create({"$target": "builtins.dict", **content})
    experiment = instantiate(config)
    models = [
        experiment["model"],
        experiment["trainer"].kwargs["model"],
        experiment["tester"]["models"][0]["model"],
        experiment["same"],
    ]
    assert all(isinstance(model, targets.Item) for model in models)
    assert len({id(model) for model in models}) == 4
    assert targets.CALLS.count("model") == 4


def test_symbol_gives_the_same_object_everywhere(targets: ModuleType):
    config = OmegaConf.create(
        {
            "$target": "config_targets.Item",
            "settings": {"$symbol": "config_targets.SETTINGS"},
            "again": "${settings}",
            "pair": ({"$symbol": "config_targets.SETTINGS"}, 1),
        }
    )
    kwargs = instantiate(config).kwargs
    assert kwargs["settings"] is targets.SETTINGS
    assert kwargs["again"] is targets.SETTINGS
    assert kwargs["pair"][0] is targets.SETTINGS


def test_partial_gives_a_partial_of_the_target(targets: ModuleType):
    config = OmegaConf.create(
        {
            "$target": "builtins.dict",
            "make": {
                "$target": "config_targets.Item",
                "$partial": True,
                "name": "made",
                "inner": {"$target": "config_targets.Item", "name": "inner"},
            },
            "built": {"$target": "config_targets.Item", "$partial": False},
        }
    )
    experiment = instantiate(config)
    assert isinstance(experiment["make"], functools.partial)
    assert isinstance(experiment["built"], targets.Item)
    assert targets.CALLS == ["inner", None]
    first = experiment["make"](name="first")
    second = experiment["make"]()
    assert first.kwargs["name"] == "first"
    assert second.kwargs["name"] == "made"
    assert first.kwargs["inner"] is second.kwargs["inner"]


def test_prepare_defers_the_node_itself(targets: ModuleType):
    config = OmegaConf.create(
        {
            "$target": "config_targets.Item",
            "inner": {"$target": "config_targets.Item", "name": "inner"},
            "later": {"$target": "config_targets.Item", "$partial": True},
        }
    )
    make_item = prepare(config)
    assert isinstance(make_item, functools.partial)
    assert targets.CALLS == ["inner"]
    item = make_item(name="called")
    assert item.kwargs["name"] == "called"
    assert isinstance(item.kwargs["inner"], targets.Item)
    assert isinstance(item.kwargs["later"], functools.partial)


@pytest.mark.parametrize("path", ["Configured", "FACTORY"])
def test_target_with_from_config_receives_the_arguments(targets: ModuleType, path: str):
    config = OmegaConf.create(
        {
            "$target": "builtins.dict",
            "now": {
                "$target": f"config_targets.{path}",
                "width": 3,
                "inner": {"$target": "config_targets.Item"},
            },
            "later": {
                "$target": f"config_targets.{path}",
                "$partial": True,
                "a": 1,
            },
        }
    )
    experiment = instantiate(config)
    assert isinstance(experiment["now"], targets.Configured)
    assert experiment["now"].config["width"] == 3
    assert isinstance(experiment["now"].config["inner"], targets.Item)
    assert experiment["now"].kwargs == {}
    later = experiment["later"](depth=2)
    assert later.config == {"a": 1}
    assert later.kwargs == {"depth": 2}


def test_args_are_the_positional_arguments_of_the_target():
    config = OmegaConf.create(
        {
            "seed": 3,
            "parts": ["runs", "mlp"],
            "path": {"$target": "pathlib.PurePosixPath", "$args": "${parts}"},
            "mask": {"$target": "builtins.int", "$args": ["ff"], "base": 16},
            "empty": {"$target": "builtins.list", "$args": []},
            "steps": {"$target": "builtins.range", "$args": ("${seed}", 10)},
            "power": {"$target": "builtins.pow", "$partial": True, "$args": [2]},
        }
    )
    assert instantiate(config.path) == pathlib.PurePosixPath("runs/mlp")
    assert instantiate(config.mask) == 255
    assert instantiate(config.empty) == []
    assert instantiate(config.steps) == range(3, 10)
    assert instantiate(config.power)(10) == 1024


def test_dataclass_binds_args_to_its_fields(targets: ModuleType):
    optimizer = {"$target": "config_targets.Optimizer", "$args": ["0.5", "3"]}
    config = OmegaConf.create(optimizer)
    assert instantiate(config) == targets.Optimizer(lr=0.5, steps=3)
    config = OmegaConf.create({**optimizer, "$args": ["0.5"], "mode": "slow"})
    assert instantiate(config) == targets.Optimizer(lr=0.5, mode=targets.Mode.SLOW)
    make_optimizer = instantiate(OmegaConf.create({**optimizer, "$partial": True}))
    assert make_optimizer(mode=targets.Mode.SLOW).steps == 3
    scaled = OmegaConf.create({"$target": "config_targets.Scaled", "$args": ["2", 3]})
    assert instantiate(scaled) == targets.Scaled(2, 3)


@pytest.mark.parametrize(
    ("node", "error_type", "full_key"),
    [
        ({"$args": [0.5], "lr": 1}, ConfigSchemaError, "optimizer"),
        (
            {"$args": [0.5, 3, "slow", [0, 1], "logs", 6]},
            ConfigSchemaError,
            "optimizer",
        ),
        ({"$args": ["fast"]}, ConfigSchemaError, "optimizer.$args[0]"),
        ({"$args": [], "steps": 3}, ConfigSchemaError, "optimizer"),
    ],
)
def test_args_that_do_not_fit_a_dataclass_are_rejected(
    targets: ModuleType,
    node: dict[str, Any],
    error_type: type[Exception],
    full_key: str,
):
    optimizer = {"$target": "config_targets.Optimizer", **node}
    config = OmegaConf.create({"optimizer": optimizer})
    with pytest.raises(error_type) as error_info:
        instantiate(config.optimizer)
    error_info.match(re.escape(f"at `{full_key}`"))
    assert targets.CALLS == []


def test_items_of_args_are_built_before_the_keyword_arguments(targets: ModuleType):
    config = OmegaConf.create(
        {
            "$target": "config_targets.make_item",
            "last": {"$target": "config_targets.Item", "name": "keyword"},
            "$args": [
                {"$target": "config_targets.Item", "name": "first"},
                {"layers": [{"$target": "config_targets.Item", "name": "nested"}]},
                {"$symbol": "config_targets.ITEM"},
            ],
        }
    )
    with pytest.raises(TypeError) as error_info:
        instantiate(config)
    error_info.match(re.escape("while calling `config_targets.make_item` at the root"))
    assert targets.CALLS == ["first", "nested", "keyword"]


def test_target_and_partial_can_be_interpolations():
    config = OmegaConf.create(
        {
            "name": "Fraction",
            "defer": True,
            "half": {"$target": "fractions.${name}", "$partial": "${defer}"},
        }
    )
    assert instantiate(config.half)() == 0


def test_meta_is_not_passed_as_an_argument():
    config = OmegaConf.create(
        {"$target": "builtins.dict", "$meta": 1, "plain": {"$meta": "???", "n": 3}}
    )
    assert instantiate(config) == {"plain": {"n": 3}}


def test_object_is_returned_as_it_is():
    config = OmegaConf.create({"$target": "builtins.dict", "n": 3})
    assert type(instantiate(config)) is dict


@pytest.mark.parametrize("content", [{"width": 3}, {"$symbol": "math.sqrt"}])
def test_node_without_a_target_is_rejected(content: dict[str, Any]):
    config = OmegaConf.create({"model": content})
    with pytest.raises(ConfigTargetError, match="`model`"):
        instantiate(config.model)
    with pytest.raises(ConfigTargetError, match="the root"):
        prepare(config)


@pytest.mark.parametrize(
    ("node", "error_type"),
    [
        ({"$target": "config_targets.Item", "lr": "???"}, ValidationMissingValueError),
        (
            {"$target": "config_targets.Item", "lr": "${nowhere}"},
            ValidationInterpolationError,
        ),
        ({"$target": "config_targets.NoSuchName"}, QualifiedNameNotFoundError),
        ({"$target": "config_targets.Item", "$foo": 1}, ConfigValidationError),
        ({"$symbol": "config_targets.NoSuchName"}, QualifiedNameNotFoundError),
    ],
)
def test_nothing_is_called_if_a_later_node_is_invalid(
    targets: ModuleType, node: dict[str, Any], error_type: type[Exception]
):
    content = {
        "$target": "config_targets.Item",
        "first": {"$target": "config_targets.Item"},
        "later": [node],
    }
    config = OmegaConf.create(content)
    with pytest.raises(error_type) as error_info:
        instantiate(config)
    error_info.match(re.escape("later[0]"))
    assert targets.CALLS == []
    assert config == content


def test_config_that_contains_itself_is_rejected(targets: ModuleType):
    config = OmegaConf.create(
        {
            "$target": "config_targets.Item",
            "a": {"$target": "config_targets.Item", "other": "${b}"},
            "b": {"$target": "config_targets.Item", "others": [{"other": "${a}"}]},
        }
    )
    with pytest.raises(ConfigValidationError, match="`a` -> `b`"):
        instantiate(config)
    assert targets.CALLS == []


def test_error_of_the_target_passes_through_with_a_note(targets: ModuleType):
    content = {
        "name": "fail",
        "model": {
            "$target": "builtins.dict",
            "first": {"$target": "config_targets.Item"},
            "parts": [{"$target": "config_targets.${name}"}],
        },
    }
    config = OmegaConf.create(content)
    with pytest.raises(UnicodeDecodeError) as error_info:
        instantiate(config.model)
    error_info.match(
        re.escape("while calling `config_targets.fail` at `model.parts[0]`")
    )
    assert config == content


def test_node_of_make_node_builds_the_target():
    node = make_node(fractions.Fraction, numerator=1, denominator=2)
    assert instantiate(OmegaConf.create(node)) == fractions.Fraction(1, 2)
    node = make_node(fractions.Fraction, 3, 4)
    assert instantiate(OmegaConf.create(node)) == fractions.Fraction(3, 4)


def test_dataclass_is_built_from_converted_values(targets: ModuleType):
    content = {
        "$target": "config_targets.Optimizer",
        "lr": "${rate}",
        "mode": "slow",
        "betas": [0.5, "0.75"],
    }
    config = OmegaConf.create({"rate": "1e-3", "optimizer": content})
    optimizer = instantiate(config.optimizer)
    assert type(optimizer) is targets.Optimizer
    assert optimizer.lr == 0.001
    assert optimizer.steps == 10
    assert optimizer.mode is targets.Mode.SLOW
    assert optimizer.betas == (0.5, 0.75)
    assert optimizer.total == pytest.approx(0.01)
    assert targets.CALLS == ["optimizer"]
    assert config == {"rate": "1e-3", "optimizer": content}


def test_configurable_receives_the_checked_values_as_a_dict(targets: ModuleType):
    config = OmegaConf.create(
        {
            "$target": "config_targets.Model",
            "depth": "4",
            "encoder": {"$target": "config_targets.SmallItem", "name": "encoder"},
        }
    )
    model = instantiate(config)
    assert type(model) is targets.Model
    assert type(model.config) is dict
    assert list(model.config) == ["depth", "encoder"]
    assert model.config["depth"] == 4
    assert type(model.config["encoder"]) is targets.SmallItem
    assert model.kwargs == {}


def test_dataclass_is_built_from_the_objects_of_its_fields(targets: ModuleType):
    content = {
        "$target": "config_targets.Experiment",
        "model": {"$target": "config_targets.Model", "depth": 2},
        "optimizer": {
            "$target": "config_targets.Optimizer",
            "lr": "0.5",
            "steps": "${seed}",
        },
        "seed": "3",
        "items": [{"$target": "config_targets.Item", "name": "listed"}],
        "named_items": {"first": {"$target": "config_targets.SmallItem"}},
        "stages": [
            {"$target": "config_targets.Optimizer", "lr": 1},
            {"$target": "config_targets.FastOptimizer", "lr": 2},
        ],
        "schedule": {"$target": "config_targets.Item", "$partial": True},
        "extra": {"anything": [{"$target": "config_targets.Item", "name": "extra"}]},
    }
    config = OmegaConf.create(content)
    OmegaConf.set_readonly(config, True)
    experiment = instantiate(config, targets.Experiment)
    assert type(experiment) is targets.Experiment
    assert type(experiment.model) is targets.Model
    assert experiment.optimizer == targets.Optimizer(lr=0.5, steps=3)
    assert experiment.seed == 3
    assert type(experiment.items[0]) is targets.Item
    assert type(experiment.named_items["first"]) is targets.SmallItem
    assert [type(stage) for stage in experiment.stages] == [
        targets.Optimizer,
        targets.FastOptimizer,
    ]
    assert isinstance(experiment.schedule, functools.partial)
    assert type(experiment.extra["anything"][0]) is targets.Item
    assert config == content


def test_field_that_is_annotated_with_a_schema_holds_a_dict(targets: ModuleType):
    model = {"$target": "config_targets.Model", "depth": 2}
    encoder = {"$target": "config_targets.Item"}
    config = OmegaConf.create(
        {
            "$target": "config_targets.Experiment",
            "model": model,
            "backbone": {"depth": "3", "encoder": encoder},
        }
    )
    backbone = instantiate(config, targets.Experiment).backbone
    assert type(backbone) is dict
    assert backbone["depth"] == 3
    assert type(backbone["encoder"]) is targets.Item
    config.backbone = {"$target": "config_targets.Model", "depth": "3"}
    with pytest.raises(ConfigSchemaError):
        instantiate(config, targets.Experiment)


def test_every_position_of_a_tuple_follows_its_annotation(targets: ModuleType):
    config = OmegaConf.create(
        {
            "$target": "config_targets.Experiment",
            "model": {"$target": "config_targets.Model", "depth": 2},
            "pair": [{"$target": "config_targets.SmallItem"}, "0.5"],
            "phases": [{"depth": "1"}, {"depth": 2, "activation": "tanh"}],
        }
    )
    experiment = instantiate(config)
    assert type(experiment.pair) is tuple
    assert type(experiment.pair[0]) is targets.SmallItem
    assert experiment.pair[1] == 0.5
    assert experiment.phases == ({"depth": 1}, {"depth": 2, "activation": "tanh"})


def test_dict_of_a_symbol_is_checked_against_the_schema(targets: ModuleType):
    config = OmegaConf.create(
        {
            "$target": "config_targets.Experiment",
            "model": {"$target": "config_targets.Model", "depth": 2},
            "backbone": {"$symbol": "config_targets.BACKBONE"},
        }
    )
    experiment = instantiate(config)
    assert experiment.backbone == {"depth": 3}
    assert targets.BACKBONE == {"depth": "3"}


def test_target_that_names_a_schema_is_rejected(targets: ModuleType):
    config = OmegaConf.create({"$target": "config_targets.ModelConfig", "depth": 3})
    with pytest.raises(ConfigSchemaError, match="ModelConfig"):
        instantiate(config)


def test_field_that_is_not_given_keeps_the_default_of_its_dataclass(
    targets: ModuleType,
):
    config = OmegaConf.create(
        {
            "$target": "config_targets.Experiment",
            "model": {"$target": "config_targets.Model", "depth": 2},
        }
    )
    experiment = instantiate(config, targets.Experiment)
    # Built once by the default factory, not a second time from its values
    assert targets.CALLS.count("optimizer") == 1
    assert experiment.optimizer == targets.Optimizer(lr=0.1)
    assert experiment.items == []


def test_every_read_of_a_dataclass_field_builds_its_own_object(targets: ModuleType):
    config = OmegaConf.create(
        {
            "shared": {"$target": "config_targets.Optimizer", "lr": 1},
            "item": {"$target": "config_targets.Item"},
            "experiment": {
                "$target": "config_targets.Experiment",
                "model": {"$target": "config_targets.Model", "depth": 2},
                "optimizer": "${shared}",
                "stages": ["${shared}", "${shared}"],
                "items": ["${item}", "${item}"],
            },
        }
    )
    experiment = instantiate(config.experiment, targets.Experiment)
    optimizers = [experiment.optimizer, *experiment.stages]
    assert all(type(optimizer) is targets.Optimizer for optimizer in optimizers)
    assert len({id(optimizer) for optimizer in optimizers}) == 3
    assert experiment.items[0] is not experiment.items[1]


def test_interpolation_reads_the_config_as_it_is_written(targets: ModuleType):
    config = OmegaConf.create(
        {
            "$target": "config_targets.Model",
            "depth": "4",
            "encoder": {"$target": "config_targets.Item", "depth": "${..depth}"},
        }
    )
    model = instantiate(config)
    assert model.config["depth"] == 4
    assert model.config["encoder"].kwargs["depth"] == "4"


def test_prepare_defers_a_node_with_a_schema(targets: ModuleType):
    config = OmegaConf.create({"$target": "config_targets.Model", "depth": "4"})
    make_model = prepare(config)
    assert isinstance(make_model, functools.partial)
    model = make_model(name="called")
    assert model.config == {"depth": 4}
    assert model.kwargs == {"name": "called"}
    optimizer = {"$target": "config_targets.Optimizer", "lr": 1}
    make_optimizer = prepare(OmegaConf.create(optimizer), targets.Optimizer)
    assert targets.CALLS == []
    assert make_optimizer(steps=3) == targets.Optimizer(lr=1.0, steps=3)


def test_partial_is_completed_when_it_is_called(targets: ModuleType):
    content = {"$target": "config_targets.Model", "activation": "tanh"}
    config = OmegaConf.create({"model": {**content, "$partial": True}, "root": content})
    make_models = {"model": instantiate(config.model), "root": prepare(config.root)}
    for key, make_model in make_models.items():
        model = make_model(depth=3, name="called")
        assert model.config == {"activation": "tanh", "depth": 3}
        assert model.kwargs == {"name": "called"}
        assert make_model(depth=3, activation="relu").config["activation"] == "relu"
        with pytest.raises(ConfigSchemaError, match="depth") as error_info:
            make_model()
        error_info.match(re.escape(f"at `{key}`"))
    with pytest.raises(ConfigSchemaError):
        instantiate(config.root)


def test_partial_of_a_dataclass_is_a_partial_of_the_class(targets: ModuleType):
    config = OmegaConf.create({"$target": "config_targets.Optimizer", "steps": "3"})
    make_optimizer = prepare(config)
    assert make_optimizer.func is targets.Optimizer
    assert make_optimizer(lr=0.5) == targets.Optimizer(lr=0.5, steps=3)
    with pytest.raises(TypeError):
        make_optimizer()


@pytest.mark.parametrize(
    ("values", "error_type"),
    [
        ({"seed": "many"}, ConfigSchemaError),
        (
            {"stages": [{"$target": "config_targets.Optimizer", "lr": "fast"}]},
            ConfigSchemaError,
        ),
        (
            {"items": [{"$target": "config_targets.Model", "depth": 1}]},
            ConfigSchemaError,
        ),
        ({"optimizer": {"lr": 1}}, ConfigSchemaError),
    ],
)
def test_nothing_is_called_if_a_value_does_not_match_its_schema(
    targets: ModuleType, values: dict[str, Any], error_type: type[Exception]
):
    content = {
        "$target": "config_targets.Experiment",
        "model": {"$target": "config_targets.Model", "depth": 2},
        "optimizer": {"$target": "config_targets.Optimizer", "lr": 1},
        "extra": {"$target": "config_targets.Item"},
        **values,
    }
    config = OmegaConf.create(content)
    with pytest.raises(error_type):
        instantiate(config, targets.Experiment)
    assert targets.CALLS == []
    assert config == content


def test_partial_fits_where_a_callable_is_expected(targets: ModuleType):
    partial_item = {"$target": "config_targets.Item", "$partial": True}
    model = {"$target": "config_targets.Model", "depth": 2}
    experiment = {"$target": "config_targets.Experiment", "model": model}
    config = OmegaConf.create({**experiment, "schedule": partial_item})
    assert isinstance(
        instantiate(config, targets.Experiment).schedule, functools.partial
    )
    targets.CALLS.clear()
    for values in ({"items": [partial_item]}, {"model": {**model, "$partial": True}}):
        with pytest.raises(ConfigSchemaError, match="a partial of"):
            instantiate(OmegaConf.create({**experiment, **values}), targets.Experiment)
    with pytest.raises(ConfigSchemaError, match="a partial of"):
        instantiate(OmegaConf.create(partial_item), targets.Item)
    item = OmegaConf.create({"$target": "config_targets.Item"})
    assert isinstance(prepare(item, targets.Item), functools.partial)
    assert targets.CALLS == []


def test_result_is_checked_against_the_class(targets: ModuleType):
    item = OmegaConf.create({"$target": "config_targets.make_item", "name": "made"})
    assert type(instantiate(item, targets.Item)) is targets.Item
    for path in ("make_item", "FACTORY"):
        config = OmegaConf.create({"$target": f"config_targets.{path}"})
        with pytest.raises(ConfigSchemaError, match="returned") as error_info:
            instantiate(config, targets.Optimizer)
        error_info.match(re.escape("at the root"))


def test_result_of_a_function_is_checked_in_a_field(targets: ModuleType):
    experiment = {
        "$target": "config_targets.Experiment",
        "model": {"$target": "config_targets.Model", "depth": 2},
    }
    made_item = {"$target": "config_targets.make_item", "name": "made"}
    config = OmegaConf.create({**experiment, "items": [made_item]})
    assert type(instantiate(config).items[0]) is targets.Item
    config = OmegaConf.create({**experiment, "optimizer": made_item})
    with pytest.raises(ConfigSchemaError, match="returned") as error_info:
        instantiate(config)
    error_info.match(re.escape("at `optimizer`"))


def test_prepare_cannot_check_the_result_of_a_function(targets: ModuleType):
    config = OmegaConf.create({"$target": "config_targets.make_item"})
    assert type(prepare(config)()) is targets.Item
    with pytest.raises(ConfigSchemaError, match="make_item"):
        prepare(config, targets.Item)


def test_schema_is_not_the_class_of_a_result(targets: ModuleType):
    model = OmegaConf.create({"$target": "config_targets.Model", "depth": 1})
    with pytest.raises(ConfigSchemaError, match="ModelConfig"):
        instantiate(model, targets.ModelConfig)
    with pytest.raises(ConfigTargetError, match="the root"):
        instantiate(OmegaConf.create({"depth": 1}), targets.ModelConfig)
    assert targets.CALLS == []


def test_schema_without_anything_to_build_is_rejected(targets: ModuleType):
    with pytest.raises(ConfigSchemaError):
        instantiate(OmegaConf.create({"depth": 1}), targets.Model)
    with pytest.raises(ConfigSchemaError, match="a mapping"):
        instantiate(OmegaConf.create({"lr": 1}), targets.Optimizer)
    with pytest.raises(ConfigTargetError, match="the root"):
        prepare(OmegaConf.create({"$symbol": "config_targets.SETTINGS"}), dict)


@pytest.mark.parametrize("content", [[{"$target": "builtins.dict"}], (1, 2)])
def test_list_is_rejected(content: Any):
    with pytest.raises(ConfigTargetError, match="the root"):
        instantiate(OmegaConf.create(content))


def test_configurable_that_is_a_dataclass_is_checked_as_one(targets: ModuleType):
    config = OmegaConf.create({"$target": "config_targets.Layer", "width": "3"})
    assert instantiate(config) == targets.Layer(width=3)
    config.width = "wide"
    with pytest.raises(ConfigSchemaError):
        instantiate(config)


@pytest.mark.parametrize("text", ["${depth}", "a \\${depth}", "${unbalanced"])
def test_text_is_not_read_as_an_interpolation_again(targets: ModuleType, text: str):
    OmegaConf.register_resolver("test_text", lambda: text, replace=True)
    config = OmegaConf.create(
        {
            "$target": "config_targets.Optimizer",
            "lr": 1,
            "log_dir": "${test_text:}",
            "steps": "${test_text:}",
        }
    )
    with pytest.raises(ConfigSchemaError, match="steps"):
        instantiate(config, targets.Optimizer)
    del config["steps"]
    assert str(instantiate(config, targets.Optimizer).log_dir) == text


def test_symbol_and_resolver_give_values_and_objects_of_typed_fields(
    targets: ModuleType,
):
    OmegaConf.register_resolver("test_item", targets.SmallItem, replace=True)
    config = OmegaConf.create(
        {
            "$target": "config_targets.Experiment",
            "model": {"$target": "config_targets.Model", "depth": 2},
            "optimizer": {
                "$target": "config_targets.Optimizer",
                "lr": {"$symbol": "math.pi"},
            },
            "items": ["${test_item:}", {"$symbol": "config_targets.ITEM"}],
        }
    )
    experiment = instantiate(config, targets.Experiment)
    assert experiment.optimizer.lr == pytest.approx(3.14159, abs=1e-5)
    assert type(experiment.items[0]) is targets.SmallItem
    assert experiment.items[1] is targets.ITEM


def test_plain_dict_is_built_like_a_config(targets: ModuleType):
    node = {"$target": "config_targets.Item", "name": "plain"}
    item = instantiate(node)
    assert type(item) is targets.Item
    assert item.kwargs == {"name": "plain"}
    make_item = prepare(node)
    assert make_item().kwargs == {"name": "plain"}
