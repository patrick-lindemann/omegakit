import importlib
import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft7Validator
from omegaconf import OmegaConf
from omegaconf.errors import MissingMandatoryValue

from omegakit import (
    ConfigValidationError,
    generate_json_schema,
    instantiate,
    is_valid,
    load_config,
    prepare,
    validate,
)
from tests import schemas
from tests.helpers import POINT, RECORDER, Point

# Contracts: §3 Resolution timing, §4 `???` lifecycle, §5 Instantiation, §10 Typed
# configs, §11 Validation, §12 Editor schemas.

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


def test_scenario_missing_filled_by_dotlist_override(write_yaml):
    """`???` + overrides + `$class`: a dotlist override fills a slot before building."""
    path = write_yaml("main.yaml", f"point:\n  $class: {POINT}\n  x: ???\n  y: 2\n")
    assert instantiate(load_config(path, overrides=["point.x=1"]).point).x == 1
    with pytest.raises(MissingMandatoryValue, match=r"point\.x"):
        instantiate(load_config(path).point)


def test_scenario_instantiation_does_not_mutate_loaded_config(write_yaml):
    """Loaded config + `instantiate` with overrides: the input stays untouched."""
    cfg = load_config(
        write_yaml(
            "main.yaml", f"point:\n  $class: {POINT}\n  x: ${{z}}\n  y: 1\nz: 2\n"
        )
    )
    before = OmegaConf.to_yaml(cfg)
    point = instantiate(cfg.point, overrides={"y": 3})
    assert (point.x, point.y) == (2, 3)
    instantiate(cfg.point)
    assert OmegaConf.to_yaml(cfg) == before


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


def test_scenario_missing_filled_by_override_passes_schema(write_yaml):
    """`???` + overrides + schema: the filled value is validated and coerced."""
    cfg = load_config(write_yaml("main.yaml", MODEL_YAML), overrides=["model.depth=3"])
    assert instantiate(cfg.model, schemas.Model).depth == 3


def test_scenario_prepare_with_runtime_only_argument(write_yaml):
    """`prepare` + schema: runtime-only arguments pass through `**kwargs`."""
    cfg = load_config(write_yaml("main.yaml", MODEL_YAML), overrides=["model.depth=1"])
    params = [object()]
    model = prepare(cfg.model, schemas.Model)(params=params)
    assert model.extra["params"] is params


def test_scenario_enum_override_mapped_to_class(write_yaml):
    """Overrides + Enum field + custom `from_config`: `kind=B` selects class `B`."""
    cfg = load_config(
        write_yaml("main.yaml", MODEL_YAML), overrides=["model.kind=B", "model.depth=1"]
    )
    assert isinstance(instantiate(cfg.model, schemas.Model).kind, schemas.B)


def test_scenario_node_child_validated_against_its_schema():
    """`make_node()` + schema: a code-chosen child is validated by its own schema."""
    wrapper = instantiate({"$class": "tests.schemas.Wrapper", "width": "4"})
    assert wrapper.inner.width == 4
    with pytest.raises(ConfigValidationError, match="EncoderConfig"):
        instantiate({"$class": "tests.schemas.Wrapper", "width": "wide"})


def test_scenario_object_field_of_wrong_class(write_yaml):
    """Loaded config + object field: a wrong `$class` fails with the node path."""
    cfg = load_config(
        write_yaml(
            "main.yaml",
            MODEL_YAML + "  encoder:\n    $class: tests.schemas.Decoder\n",
        ),
        overrides=["model.depth=1"],
    )
    with pytest.raises(ConfigValidationError, match=r"`encoder`.*Decoder"):
        instantiate(cfg.model)


def test_scenario_resolver_object_in_any_field(write_yaml):
    """Resolver + `Any` field: an object returned by a resolver is passed through."""
    encoder = schemas.Encoder(9)
    OmegaConf.register_new_resolver("encoder", lambda: encoder)
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
    assert not is_valid(load_config(path), schema=schemas.AppConfig)
    cfg = load_config(path, overrides=["training.model.depth=${seed}"])
    validate(cfg, schema=schemas.AppConfig)
    assert instantiate(cfg.training.model, schemas.Model).depth == 4


EXAMPLES = Path(__file__).parents[2] / "docs" / "examples"
SCHEMAS = {"app.schema.json": "AppConfig", "model.schema.json": "Model"}


def _modeline_schema(path: Path) -> dict:
    first_line = path.read_text().splitlines()[0]
    name = first_line.removeprefix("# yaml-language-server: $schema=")
    return json.loads((path.parent / name).read_text())


@pytest.mark.parametrize(
    "path", sorted(EXAMPLES.rglob("*.yaml")), ids=lambda path: path.name
)
def test_scenario_example_yaml_matches_its_schema(path: Path):
    """Editor schema + real files: every example YAML validates, a typo does not."""
    validator = Draft7Validator(_modeline_schema(path))
    config = yaml.safe_load(path.read_text())
    assert list(validator.iter_errors(config)) == []
    assert list(validator.iter_errors({**config, "misspeled": 1}))


@pytest.mark.parametrize(("file", "name"), SCHEMAS.items())
def test_scenario_example_schemas_are_current(monkeypatch, file: str, name: str):
    """Generator + committed files: the example schemas match the generator."""
    monkeypatch.syspath_prepend(str(EXAMPLES))
    editor_app = importlib.import_module("editor_app")
    generated = generate_json_schema(getattr(editor_app, name))
    assert json.loads((EXAMPLES / "editor" / file).read_text()) == generated
