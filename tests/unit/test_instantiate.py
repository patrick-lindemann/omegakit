import fractions
import functools
from types import ModuleType
from typing import Any

import pytest
from omegaconf import OmegaConf

from omegakit._core.target import TargetNotFoundError
from omegakit._features.class_ import ClassSyntaxError, make_node
from omegakit.instantiate import instantiate, prepare
from omegakit.schema import SchemaTypeError, SchemaValueError
from omegakit.validate import (
    ValidationCycleError,
    ValidationInterpolationError,
    ValidationMissingValueError,
)


def test_builds_the_object_of_a_class():
    content = {"$class": "fractions.Fraction", "numerator": 1, "denominator": "${two}"}
    config = OmegaConf.create({"half": content, "two": 2})
    OmegaConf.set_readonly(config, True)
    assert instantiate(config.half) == fractions.Fraction(1, 2)
    assert config == {"half": content, "two": 2}


def test_nested_classes_are_built_as_arguments(targets: ModuleType):
    config = OmegaConf.create(
        {
            "$class": "config_targets.Item",
            "inner": {"$class": "config_targets.Item", "name": "inner"},
            "items": [{"$class": "config_targets.Item", "name": "listed"}],
            "pair": ({"$class": "config_targets.Item", "name": "paired"}, 2),
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
        "model": {"$class": "config_targets.Item", "name": "model"},
        "trainer": {"$class": "config_targets.Item", "model": "${model}"},
        "tester": {"models": [{"model": "${model}"}]},
        "same": "${model}",
    }
    if is_reversed:
        content = dict(reversed(content.items()))
    config = OmegaConf.create({"$class": "builtins.dict", **content})
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
            "$class": "config_targets.Item",
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
            "$class": "builtins.dict",
            "make": {
                "$class": "config_targets.Item",
                "$partial": True,
                "name": "made",
                "inner": {"$class": "config_targets.Item", "name": "inner"},
            },
            "built": {"$class": "config_targets.Item", "$partial": False},
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
            "$class": "config_targets.Item",
            "inner": {"$class": "config_targets.Item", "name": "inner"},
            "later": {"$class": "config_targets.Item", "$partial": True},
        }
    )
    make_item = prepare(config)
    assert isinstance(make_item, functools.partial)
    assert targets.CALLS == ["inner"]
    item = make_item(name="called")
    assert item.kwargs["name"] == "called"
    assert isinstance(item.kwargs["inner"], targets.Item)
    assert isinstance(item.kwargs["later"], functools.partial)


@pytest.mark.parametrize("import_path", ["Configured", "FACTORY"])
def test_target_with_from_config_receives_the_arguments(
    targets: ModuleType, import_path: str
):
    config = OmegaConf.create(
        {
            "$class": "builtins.dict",
            "now": {
                "$class": f"config_targets.{import_path}",
                "width": 3,
                "inner": {"$class": "config_targets.Item"},
            },
            "later": {
                "$class": f"config_targets.{import_path}",
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


def test_class_and_partial_can_be_interpolations():
    config = OmegaConf.create(
        {
            "name": "Fraction",
            "defer": True,
            "half": {"$class": "fractions.${name}", "$partial": "${defer}"},
        }
    )
    assert instantiate(config.half)() == 0


def test_meta_is_not_passed_as_an_argument():
    config = OmegaConf.create(
        {"$class": "builtins.dict", "$meta": 1, "plain": {"$meta": "???", "n": 3}}
    )
    assert instantiate(config) == {"plain": {"n": 3}}


def test_object_is_returned_as_it_is():
    config = OmegaConf.create({"$class": "builtins.dict", "n": 3})
    assert type(instantiate(config)) is dict


@pytest.mark.parametrize("content", [{"width": 3}, {"$symbol": "math.sqrt"}])
def test_node_without_a_class_is_rejected(content: dict[str, Any]):
    config = OmegaConf.create({"model": content})
    with pytest.raises(ClassSyntaxError, match="`model`"):
        instantiate(config.model)
    with pytest.raises(ClassSyntaxError, match="the root"):
        prepare(config)


@pytest.mark.parametrize(
    ("node", "error_type"),
    [
        ({"$class": "config_targets.Item", "lr": "???"}, ValidationMissingValueError),
        (
            {"$class": "config_targets.Item", "lr": "${nowhere}"},
            ValidationInterpolationError,
        ),
        ({"$class": "config_targets.NoSuchName"}, TargetNotFoundError),
        ({"$class": "config_targets.Item", "$foo": 1}, ClassSyntaxError),
        ({"$symbol": "config_targets.NoSuchName"}, TargetNotFoundError),
    ],
)
def test_nothing_is_called_if_a_later_node_is_invalid(
    targets: ModuleType, node: dict[str, Any], error_type: type[Exception]
):
    content = {
        "$class": "config_targets.Item",
        "first": {"$class": "config_targets.Item"},
        "later": [node],
    }
    config = OmegaConf.create(content)
    with pytest.raises(error_type) as error_info:
        instantiate(config)
    assert "later[0]" in "\n".join(error_info.value.__notes__)
    assert targets.CALLS == []
    assert config == content


def test_config_that_contains_itself_is_rejected(targets: ModuleType):
    config = OmegaConf.create(
        {
            "$class": "config_targets.Item",
            "a": {"$class": "config_targets.Item", "other": "${b}"},
            "b": {"$class": "config_targets.Item", "others": [{"other": "${a}"}]},
        }
    )
    with pytest.raises(ValidationCycleError, match="`a` -> `b`"):
        instantiate(config)
    assert targets.CALLS == []


def test_error_of_the_target_passes_through_with_a_note(targets: ModuleType):
    content = {
        "name": "fail",
        "model": {
            "$class": "builtins.dict",
            "first": {"$class": "config_targets.Item"},
            "parts": [{"$class": "config_targets.${name}"}],
        },
    }
    config = OmegaConf.create(content)
    with pytest.raises(UnicodeDecodeError) as error_info:
        instantiate(config.model)
    assert error_info.value.__notes__ == [
        "  while calling `config_targets.fail` at `model.parts[0]`"
    ]
    assert config == content


def test_node_of_make_node_builds_the_target():
    node = make_node(fractions.Fraction, numerator=1, denominator=2)
    assert instantiate(OmegaConf.create(node)) == fractions.Fraction(1, 2)


def test_dataclass_is_built_from_converted_values(targets: ModuleType):
    content = {
        "$class": "config_targets.Optimizer",
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


def test_configurable_receives_an_instance_of_its_schema(targets: ModuleType):
    config = OmegaConf.create(
        {
            "$class": "config_targets.Model",
            "depth": "4",
            "encoder": {"$class": "config_targets.SmallItem", "name": "encoder"},
        }
    )
    model = instantiate(config)
    assert type(model) is targets.Model
    assert type(model.config) is targets.ModelConfig
    assert model.config.depth == 4
    assert model.config.activation == "relu"
    assert type(model.config.encoder) is targets.SmallItem
    assert model.kwargs == {}


def test_schema_builds_a_root_without_a_class(targets: ModuleType):
    content = {
        "model": {"$class": "config_targets.Model", "depth": 2},
        "optimizer": {"lr": "0.5", "steps": "${seed}"},
        "seed": "3",
        "items": [{"$class": "config_targets.Item", "name": "listed"}],
        "named_items": {"first": {"$class": "config_targets.SmallItem"}},
        "stages": [{"lr": 1}, {"$class": "config_targets.FastOptimizer", "lr": 2}],
        "schedule": {"$class": "config_targets.Item", "$partial": True},
        "extra": {"anything": [{"$class": "config_targets.Item", "name": "extra"}]},
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


def test_dataclass_field_holds_what_its_node_builds(targets: ModuleType):
    model = {"$class": "config_targets.Model", "depth": 2}
    config = OmegaConf.create(
        {"model": model, "backbone": {"$class": "config_targets.Model", "depth": "3"}}
    )
    backbone = instantiate(config, targets.Experiment).backbone
    assert type(backbone) is targets.Model
    assert backbone.config == targets.ModelConfig(depth=3)
    config = OmegaConf.create({"model": model, "backbone": {"depth": "3"}})
    backbone = instantiate(config, targets.Experiment).backbone
    assert backbone == targets.ModelConfig(depth=3)


def test_field_that_is_not_given_keeps_the_default_of_its_dataclass(
    targets: ModuleType,
):
    config = OmegaConf.create({"model": {"$class": "config_targets.Model", "depth": 2}})
    experiment = instantiate(config, targets.Experiment)
    # Built once by the default factory, not a second time from its values
    assert targets.CALLS.count("optimizer") == 1
    assert experiment.optimizer == targets.Optimizer(lr=0.1)
    assert experiment.items == []


def test_every_read_of_a_dataclass_field_builds_its_own_object(targets: ModuleType):
    config = OmegaConf.create(
        {
            "shared": {"lr": 1},
            "item": {"$class": "config_targets.Item"},
            "experiment": {
                "model": {"$class": "config_targets.Model", "depth": 2},
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
            "$class": "config_targets.Model",
            "depth": "4",
            "encoder": {"$class": "config_targets.Item", "depth": "${..depth}"},
        }
    )
    model = instantiate(config)
    assert model.config.depth == 4
    assert model.config.encoder.kwargs["depth"] == "4"


def test_prepare_defers_a_node_with_a_schema(targets: ModuleType):
    config = OmegaConf.create({"$class": "config_targets.Model", "depth": "4"})
    make_model = prepare(config)
    assert isinstance(make_model, functools.partial)
    model = make_model(name="called")
    assert model.config == targets.ModelConfig(depth=4)
    assert model.kwargs == {"name": "called"}
    make_optimizer = prepare(OmegaConf.create({"lr": 1}), targets.Optimizer)
    assert targets.CALLS == []
    assert make_optimizer(steps=3) == targets.Optimizer(lr=1.0, steps=3)


@pytest.mark.parametrize(
    ("values", "error_type"),
    [
        ({"seed": "many"}, SchemaValueError),
        ({"stages": [{"lr": 1}, {"lr": "fast"}]}, SchemaValueError),
        ({"items": [{"$class": "config_targets.Model", "depth": 1}]}, SchemaTypeError),
    ],
)
def test_nothing_is_called_if_a_value_does_not_match_its_schema(
    targets: ModuleType, values: dict[str, Any], error_type: type[Exception]
):
    content = {
        "model": {"$class": "config_targets.Model", "depth": 2},
        "optimizer": {"lr": 1},
        "extra": {"$class": "config_targets.Item"},
        **values,
    }
    config = OmegaConf.create(content)
    with pytest.raises(error_type):
        instantiate(config, targets.Experiment)
    assert targets.CALLS == []
    assert config == content


def test_partial_fits_where_a_callable_is_expected(targets: ModuleType):
    partial_item = {"$class": "config_targets.Item", "$partial": True}
    model = {"$class": "config_targets.Model", "depth": 2}
    config = OmegaConf.create({"model": model, "schedule": partial_item})
    assert isinstance(
        instantiate(config, targets.Experiment).schedule, functools.partial
    )
    targets.CALLS.clear()
    for values in ({"items": [partial_item]}, {"model": {**model, "$partial": True}}):
        with pytest.raises(SchemaTypeError, match="a partial of"):
            instantiate(
                OmegaConf.create({"model": model, **values}), targets.Experiment
            )
    with pytest.raises(SchemaTypeError, match="a partial of"):
        instantiate(OmegaConf.create(partial_item), targets.Item)
    item = OmegaConf.create({"$class": "config_targets.Item"})
    assert isinstance(prepare(item, targets.Item), functools.partial)
    assert targets.CALLS == []


def test_schema_without_anything_to_build_is_rejected(targets: ModuleType):
    with pytest.raises(SchemaTypeError):
        instantiate(OmegaConf.create({"depth": 1}), targets.Model)
    with pytest.raises(ClassSyntaxError, match="the root"):
        prepare(OmegaConf.create({"$symbol": "config_targets.SETTINGS"}), dict)


@pytest.mark.parametrize("content", [[{"$class": "builtins.dict"}], (1, 2)])
def test_list_is_rejected(content: Any):
    with pytest.raises(ClassSyntaxError, match="the root"):
        instantiate(OmegaConf.create(content))


def test_configurable_that_is_a_dataclass_is_checked_as_one(targets: ModuleType):
    config = OmegaConf.create({"$class": "config_targets.Layer", "width": "3"})
    assert instantiate(config) == targets.Layer(width=3)
    config.width = "wide"
    with pytest.raises(SchemaValueError):
        instantiate(config)


@pytest.mark.parametrize("text", ["${depth}", "a \\${depth}", "${unbalanced"])
def test_text_is_not_read_as_an_interpolation_again(targets: ModuleType, text: str):
    OmegaConf.register_resolver("test_text", lambda: text, replace=True)
    config = OmegaConf.create(
        {"lr": 1, "log_dir": "${test_text:}", "steps": "${test_text:}"}
    )
    with pytest.raises(SchemaValueError, match="steps"):
        instantiate(config, targets.Optimizer)
    del config["steps"]
    assert str(instantiate(config, targets.Optimizer).log_dir) == text


def test_symbol_and_resolver_give_values_and_objects_of_typed_fields(
    targets: ModuleType,
):
    OmegaConf.register_resolver("test_item", targets.SmallItem, replace=True)
    config = OmegaConf.create(
        {
            "model": {"$class": "config_targets.Model", "depth": 2},
            "optimizer": {"lr": {"$symbol": "math.pi"}},
            "items": ["${test_item:}", {"$symbol": "config_targets.ITEM"}],
        }
    )
    experiment = instantiate(config, targets.Experiment)
    assert experiment.optimizer.lr == pytest.approx(3.14159, abs=1e-5)
    assert type(experiment.items[0]) is targets.SmallItem
    assert experiment.items[1] is targets.ITEM
