import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

import pytest
from omegaconf import OmegaConf

from omegakit import (
    Configurable,
    ConfigValidationError,
    instantiate,
    load_config,
    validate,
)
from tests import schemas
from tests.helpers import FAILING

# Contracts: §11 Validation.

MODEL = "tests.schemas.Model"

APP = """\
seed: 3
data:
  batch_size: "64"
training:
  epochs: 2
  model:
    $class: tests.schemas.Model
    kind: B
    depth: ${seed}
    encoder:
      $class: tests.schemas.Encoder
      width: 8
"""


def _model(**fields):
    return {"$class": MODEL, "depth": 1, **fields}


def test_validate_accepts_a_loaded_config(write_yaml):
    cfg = load_config(write_yaml("app.yaml", APP))
    validate(cfg, schema=schemas.AppConfig)


def test_validate_returns_nothing_and_leaves_the_config_unchanged(write_yaml):
    cfg = load_config(write_yaml("app.yaml", APP))
    before = OmegaConf.to_container(cfg)
    assert validate(cfg, schema=schemas.AppConfig) is None
    assert OmegaConf.to_container(cfg) == before


def test_validate_builds_nothing():
    validate({"child": {"$class": FAILING}})


HOOK_CALLS: list[int] = []


@dataclass
class Hooked:
    x: int

    def __post_init__(self) -> None:
        HOOK_CALLS.append(self.x)


@dataclass
class HookedConfig:
    hooked: Hooked
    items: list[Hooked]


class WithHooked(Configurable[HookedConfig]):
    def __init__(self, **fields: Any) -> None:
        self.fields = fields


def test_validate_constructs_no_schema_dataclasses():
    HOOK_CALLS.clear()
    values = {"hooked": {"x": 1}, "items": [{"x": 2}]}
    validate({"$class": f"{__name__}.WithHooked", **values})
    validate(values, schema=HookedConfig)
    assert HOOK_CALLS == []
    instantiate({"$class": f"{__name__}.WithHooked", **values})
    assert HOOK_CALLS == [1, 2]


def test_validate_checks_root_values_against_the_schema(write_yaml):
    cfg = load_config(write_yaml("app.yaml", APP.replace('"64"', "many")))
    with pytest.raises(ConfigValidationError, match=r"Value .many. of type"):
        validate(cfg, schema=schemas.AppConfig)


@pytest.mark.parametrize("key", ["sed", "data.batch", "training.epoch"])
def test_validate_rejects_unknown_keys(key):
    config = {"training": {"model": _model()}}
    OmegaConf.update(config := OmegaConf.create(config), key, 1, force_add=True)
    with pytest.raises(ConfigValidationError, match=key.split(".")[-1]):
        validate(config, schema=schemas.AppConfig)


def test_validate_rejects_missing_required_fields():
    with pytest.raises(ConfigValidationError, match="Missing required field `model`"):
        validate({"training": {}}, schema=schemas.AppConfig)


def test_validate_checks_class_nodes_without_a_root_schema():
    with pytest.raises(ConfigValidationError, match=r"`model\.depth` \(ModelConfig\)"):
        validate({"model": _model(depth="deep")})
    with pytest.raises(ConfigValidationError, match=r"Unknown field.*'dpth'"):
        validate({"items": [{"$class": MODEL, "dpth": 1}]})


def test_validate_checks_nested_class_nodes_bottom_up():
    encoder = {"$class": "tests.schemas.TypedEncoder", "width": "wide"}
    with pytest.raises(ConfigValidationError, match=r"`model\.encoder\.width`"):
        validate({"model": _model(encoder=encoder)})


def test_validate_rejects_unresolved_values():
    with pytest.raises(ConfigValidationError, match="Cannot resolve"):
        validate({"model": _model(depth="???")})
    with pytest.raises(ConfigValidationError, match="Cannot resolve"):
        validate({"model": _model(depth="${nowhere}")})


def test_validate_accepts_subclasses_for_object_fields():
    validate(
        {
            "$class": MODEL,
            "depth": 1,
            "encoder": {"$class": "tests.schemas.WideEncoder"},
        }
    )
    config = {"training": {"model": _model()}}
    validate(config, schema=schemas.AppConfig)


def test_validate_rejects_other_classes_for_object_fields():
    config = _model(encoder={"$class": "tests.schemas.Decoder"})
    with pytest.raises(ConfigValidationError, match="`encoder` expects Encoder"):
        validate(config)


def test_validate_skips_the_class_check_for_functions_and_partials():
    validate(_model(encoder={"$class": "tests.schemas.make_encoder", "width": 2}))
    validate(_model(encoder={"$class": "tests.schemas.Decoder", "$partial": True}))


def test_validate_checks_refs_by_instance():
    validate(
        {
            "$class": "tests.schemas.Fields",
            "factory": {"$ref": "tests.schemas.make_encoder"},
        }
    )
    with pytest.raises(ConfigValidationError, match="`encoder` expects Encoder"):
        validate(_model(encoder={"$ref": "tests.schemas.Encoder"}))
    with pytest.raises(ConfigValidationError, match="cannot contain any other keys"):
        validate(_model(encoder={"$ref": "tests.schemas.Encoder", "width": 1}))


def test_validate_object_fields_need_a_class_node():
    with pytest.raises(ConfigValidationError, match="mapping without `\\$class`"):
        validate(_model(encoder={"width": 1}))
    with pytest.raises(ConfigValidationError, match="gives `3`"):
        validate(_model(encoder=3))


def test_validate_none_needs_an_optional_field():
    validate(_model(encoder=None))
    with pytest.raises(ConfigValidationError, match="gives `None`"):
        validate({"$class": "tests.schemas.RequiredObject", "encoder": None})


def test_validate_walks_any_fields_and_classes_without_schema():
    bad = [_model(depth="deep")]
    with pytest.raises(ConfigValidationError, match=r"`callbacks\.0\.depth`"):
        validate(
            {"training": {"model": _model()}, "callbacks": bad},
            schema=schemas.AppConfig,
        )
    with pytest.raises(ConfigValidationError, match=r"`fields\.0\.depth`"):
        validate({"$class": "tests.schemas.Untyped", "fields": bad})


def test_validate_ignores_meta():
    validate({"$meta": {"note": 1}, "model": _model(**{"$meta": {"note": 2}})})


def test_validate_rejects_reserved_keys():
    with pytest.raises(ConfigValidationError, match="`\\$base`"):
        validate({"model": _model(**{"$base": {}})})
    with pytest.raises(ConfigValidationError, match="`\\$other`"):
        validate({"section": {"$other": 1}})
    with pytest.raises(ConfigValidationError, match="must be `true` or `false`"):
        validate({"model": _model(**{"$partial": "yes"})})


def test_validate_rejects_unimportable_classes():
    with pytest.raises(ConfigValidationError, match="Cannot import `Nope`"):
        validate({"thing": {"$ref": "Nope"}})
    with pytest.raises(
        ConfigValidationError, match=r"Cannot import `tests\.schemas\.Nope`"
    ):
        validate({"model": {"$class": "tests.schemas.Nope"}})
    with pytest.raises(ConfigValidationError, match="Cannot import `Nope`"):
        validate({"model": {"$class": "Nope"}})


@pytest.mark.parametrize("key", ["$class", "$ref"])
@pytest.mark.parametrize("value", [123, None, ["math.pi"]])
def test_validate_rejects_import_paths_that_are_not_strings(key, value):
    with pytest.raises(ConfigValidationError, match=rf"`\{key}` in `thing`"):
        validate({"thing": {key: value}})
    with pytest.raises(ConfigValidationError, match=rf"`\{key}` in `thing`"):
        instantiate({"$class": "tests.helpers.Recorder", "thing": {key: value}})


class Runner(Protocol):
    def run(self) -> None: ...


@dataclass
class UntypedFieldsConfig:
    function: Callable[..., Any] | None = None
    runner: Runner | None = None


class WithUntypedFields(Configurable[UntypedFieldsConfig]):
    def __init__(self, **fields: Any) -> None:
        self.fields = fields


@pytest.mark.parametrize(
    ("values", "match"),
    [
        ({"function": {"$foo": 1}}, r"`\$foo` in `function`"),
        ({"function": {"$partial": "yes"}}, r"`\$partial` in `function`"),
        ({"function": [{"$ref": "math.sqrt", "a": 1}]}, r"`function\.0` has"),
        ({"function": [{"$class": "tests.no_such_module.X"}]}, r"in `function\.0`"),
        ({"runner": {"$foo": 1}}, r"`\$foo` in `runner`"),
        ({"runner": {"a": {"$class": "tests.no_such_module.X"}}}, r"`runner\.a`"),
    ],
)
def test_validate_checks_reserved_keys_under_untyped_object_fields(values, match):
    config = {"$class": f"{__name__}.WithUntypedFields", **values}
    with pytest.raises(ConfigValidationError, match=match):
        validate(config)
    with pytest.raises(ConfigValidationError, match=match):
        instantiate(config)


def test_validate_rejects_a_missing_target_module():
    with pytest.raises(ConfigValidationError, match="Cannot import") as info:
        validate({"thing": {"$class": "tests.no_such_module.Thing"}})
    assert isinstance(info.value.__cause__, ModuleNotFoundError)


@pytest.mark.parametrize(
    ("source", "error"),
    [
        ("import no_such_dependency\n", ModuleNotFoundError),
        ("from os import no_such_name\n", ImportError),
    ],
)
def test_validate_propagates_import_errors_from_the_target_module(
    tmp_path, monkeypatch, source, error
):
    (tmp_path / "broken_target.py").write_text(source + "class Thing: ...\n")
    monkeypatch.syspath_prepend(tmp_path)
    monkeypatch.delitem(sys.modules, "broken_target", raising=False)
    with pytest.raises(error) as info:
        validate({"thing": {"$class": "broken_target.Thing"}})
    assert not isinstance(info.value, ConfigValidationError)


@pytest.mark.parametrize("import_path", ["nodots", ".Foo", "..mod.X", "mod.", "a..b"])
def test_validate_rejects_malformed_import_paths(import_path):
    with pytest.raises(ConfigValidationError, match="is not an import path"):
        validate({"thing": {"$class": import_path}})


def test_validate_rejects_class_targets_that_cannot_be_built():
    with pytest.raises(ConfigValidationError, match=r"math\.pi` in `thing`"):
        validate({"thing": {"$class": "math.pi"}})
    with pytest.raises(ConfigValidationError, match=r"math\.pi` in `thing`"):
        instantiate(
            {"$class": "tests.helpers.Recorder", "thing": {"$class": "math.pi"}}
        )
    validate({"thing": {"$ref": "math.pi"}})


def test_validate_runs_the_schema_consistency_check():
    with pytest.raises(ConfigValidationError, match="required parameter `z`"):
        validate({"$class": "tests.schemas.MissingParameter"})


def test_validate_root_class_must_match_the_schema():
    with pytest.raises(ConfigValidationError, match="expects AppConfig"):
        validate(_model(), schema=schemas.AppConfig)


def test_validate_rejects_schemas_that_are_not_classes():
    with pytest.raises(TypeError, match="not a class"):
        validate({}, schema=schemas.make_encoder)  # pyright: ignore[reportArgumentType]


def test_validate_class_without_schema_needs_a_root_class():
    with pytest.raises(ConfigValidationError, match="no dataclass schema"):
        validate({}, schema=schemas.Encoder)


LIBRARY = """\
connection:
  host: ???
  port: 5432
  url: postgres://${.host}:${.port}/${database}
"""


def test_validate_allow_missing_accepts_open_slots_and_their_interpolations(
    write_yaml,
):
    cfg = load_config(write_yaml("library.yaml", LIBRARY))
    with pytest.raises(ConfigValidationError):
        validate(cfg)
    validate(cfg, allow_missing=True)


def test_validate_allow_missing_accepts_missing_schema_fields():
    validate({"model": {"$class": MODEL, "depth": "???"}}, allow_missing=True)
    validate({"model": {"$class": MODEL}}, allow_missing=True)
    validate({"$class": "tests.schemas.RequiredObject"}, allow_missing=True)
    with pytest.raises(ConfigValidationError, match="Missing"):
        validate({"model": {"$class": MODEL}})


def test_validate_allow_missing_still_checks_given_values():
    with pytest.raises(ConfigValidationError, match=r"`model\.depth`"):
        validate({"model": _model(depth="deep")}, allow_missing=True)
    with pytest.raises(ConfigValidationError, match="`mode`"):
        validate(
            {"mode": "test", "level": "???"},
            schema=schemas.LiteralConfig,
            allow_missing=True,
        )


@dataclass
class Required:
    x: int


@dataclass
class Fragment:
    pair: tuple[int, int] = (0, 0)
    inner: Required | int = 0


def test_validate_allow_missing_inside_tuples_and_union_members():
    validate({"pair": ["???", 2], "inner": {}}, schema=Fragment, allow_missing=True)
    with pytest.raises(ConfigValidationError, match=r"`pair\.1`"):
        validate({"pair": ["???", "x"]}, schema=Fragment, allow_missing=True)
    with pytest.raises(ConfigValidationError, match="`inner`"):
        validate({"inner": {"x": "y"}}, schema=Fragment, allow_missing=True)


def test_validate_allow_missing_keeps_defaults_for_missing_values():
    validate({"level": "???"}, schema=schemas.LiteralConfig, allow_missing=True)


def test_validate_class_schema_checks_a_fragment_without_root_class():
    validate({"depth": 1}, schema=schemas.Model)
    with pytest.raises(ConfigValidationError, match=r"Unknown field.*'dpth'"):
        validate({"dpth": 1}, schema=schemas.Model)


def test_validate_class_schema_checks_the_root_class():
    validate(_model(), schema=schemas.Model)
    with pytest.raises(ConfigValidationError, match="expects Encoder"):
        validate(_model(), schema=schemas.Encoder)
