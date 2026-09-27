import importlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self, override

import pytest
import yaml
from jsonschema import Draft7Validator

from omegakit import (
    Configurable,
    ConfigValidationError,
    generate_json_schema,
    instantiate,
    load_config,
    make_node,
    validate,
)
from omegakit.utils import register_resolver
from tests import schemas
from tests.helpers import POINT, RECORDER, Point
from tests.schemas import TypedEncoder


@dataclass
class WrapperConfig:
    width: Any = 1


class Wrapper(Configurable[WrapperConfig]):
    """Builds a code-chosen `TypedEncoder` child with `make_node`."""

    def __init__(self, inner: TypedEncoder) -> None:
        self.inner = inner

    @classmethod
    @override
    def from_config(cls, config: WrapperConfig, **kwargs: Any) -> Self:
        return cls(
            instantiate(
                make_node(TypedEncoder, width=config.width), schema=TypedEncoder
            )
        )


MODEL_YAML = "model:\n  $class: tests.schemas.Model\n  kind: A\n  depth: ???\n"


def test_scenario_defaults_give_every_item_the_same_class(write_yaml):
    """`$defaults` + `$class`: one `$defaults` makes every sibling instantiable."""
    cfg = load_config(
        write_yaml(
            "main.yaml",
            f"points:\n  $defaults: {{$class: {POINT}, y: 0}}\n"
            "  a: {x: 1}\n  b: {x: 2, y: 5}\n",
        )
    )
    points = {key: instantiate(cfg.points[key]) for key in cfg.points}
    assert all(isinstance(point, Point) for point in points.values())
    assert [(p.x, p.y) for p in points.values()] == [(1, 0), (2, 5)]


def test_scenario_imported_base_slot_filled_by_consumer(write_yaml):
    """`~import` + `$base` + `???` + `$class`: the consumer fills a library slot."""
    write_yaml("lib.yaml", f"$class: {POINT}\nx: ???\ny: 2\n")
    cfg = load_config(
        write_yaml("main.yaml", "point:\n  $base: ~import lib.yaml\n  x: 5\n")
    )
    point = instantiate(cfg.point)
    assert (point.x, point.y) == (5, 2)


def test_scenario_golden_reusable_library(write_yaml):
    """Golden case: a library with `???` slots wired by relative interpolations."""
    write_yaml(
        "sde.yaml",
        "manifold: ???\n"
        "steps: 100\n"
        "sde:\n"
        f"  $class: {RECORDER}\n"
        "  manifold: ${..manifold}\n"
        "  steps: ${..steps}\n",
    )
    cfg = load_config(
        write_yaml(
            "main.yaml",
            "model:\n  $base: ~import sde.yaml\n  manifold: SO3\n",
        )
    )
    config, _ = instantiate(cfg.model.sde)
    assert config == {"manifold": "SO3", "steps": 100}


def test_scenario_golden_dataset_manifest(write_yaml):
    """Golden case: a dataset manifest whose items share `$defaults`."""
    cfg = load_config(
        write_yaml(
            "main.yaml",
            "root: /data\n"
            "records:\n"
            "  $defaults:\n"
            f"    $class: {RECORDER}\n"
            "    path: ${root}/${.id}.h5\n"
            "    scale: 1.0\n"
            "  sphere: {id: sphere}\n"
            "  cube: {id: cube, scale: 2.0}\n",
        )
    )
    records = [instantiate(cfg.records[key])[0] for key in cfg.records]
    assert records == [
        {"id": "sphere", "path": "/data/sphere.h5", "scale": 1.0},
        {"id": "cube", "path": "/data/cube.h5", "scale": 2.0},
    ]


def test_scenario_node_child_validated_against_its_schema():
    """`make_node()` + schema: a code-chosen child is validated by its own schema."""
    wrapper = instantiate({"$class": f"{__name__}.Wrapper", "width": "4"})
    assert wrapper.inner.width == 4
    with pytest.raises(ConfigValidationError, match="EncoderConfig"):
        instantiate({"$class": f"{__name__}.Wrapper", "width": "wide"})


def test_scenario_resolver_object_in_any_field(write_yaml):
    """Resolver + `Any` field: an object returned by a resolver is passed through."""
    encoder = schemas.Encoder(9)
    register_resolver("encoder", lambda: encoder)
    cfg = load_config(
        write_yaml(
            "main.yaml",
            "fields:\n  $class: tests.schemas.Fields\n  anything: ${encoder:}\n",
        )
    )
    assert instantiate(cfg.fields).fields["anything"] is encoder


def test_scenario_validate_before_instantiating(write_yaml):
    """`~import` + `???` + overrides + `validate`: check the full config, then build."""
    write_yaml("model.yaml", "$class: tests.schemas.Model\nkind: B\ndepth: ???\n")
    path = write_yaml("main.yaml", "seed: 4\ntraining:\n  model: ~import model.yaml\n")
    with pytest.raises(ConfigValidationError, match="depth"):
        validate(load_config(path), schema=schemas.AppConfig)
    cfg = load_config(path, overrides=["training.model.depth=${seed}"])
    validate(cfg, schema=schemas.AppConfig)
    assert instantiate(cfg.training.model, schema=schemas.Model).depth == 4


def test_scenario_forward_base_to_imported_node_then_instantiate(write_yaml):
    """`$base: ${later}` + `~import` + `instantiate`: the later node merges first."""
    write_yaml("model.yaml", "$class: tests.schemas.Model\nkind: B\n")
    cfg = load_config(
        write_yaml(
            "main.yaml",
            "small:\n  $base: ${shared}\n  depth: 2\n"
            "shared:\n  $base: ~import model.yaml\n  depth: ???\n",
        )
    )
    assert instantiate(cfg.small, schema=schemas.Model).depth == 2
    with pytest.raises(ConfigValidationError, match=r"`shared\.depth`"):
        instantiate(cfg.shared)


WEBAPP = Path(__file__).parents[2] / "docs" / "webapp"


def _modeline_schema(path: Path) -> dict:
    first_line = path.read_text().splitlines()[0]
    name = first_line.removeprefix("# yaml-language-server: $schema=")
    return json.loads((path.parent / name).read_text())


@pytest.mark.parametrize(
    "path",
    sorted((WEBAPP / "configs").glob("**/*.yaml")),
    ids=lambda path: path.name,
)
def test_scenario_example_yaml_matches_its_schema(path: Path):
    """Editor schema + real files: every example YAML validates, a typo does not."""
    validator = Draft7Validator(_modeline_schema(path))
    config = yaml.safe_load(path.read_text())
    assert list(validator.iter_errors(config)) == []
    assert list(validator.iter_errors({**config, "misspeled": 1}))


def test_scenario_example_schema_is_current(monkeypatch):
    """Generator + committed file: the example schema matches the generator."""
    monkeypatch.syspath_prepend(str(WEBAPP))
    webapp = importlib.import_module("webapp")
    generated = generate_json_schema(webapp.App)
    assert json.loads((WEBAPP / "app.schema.json").read_text()) == generated
