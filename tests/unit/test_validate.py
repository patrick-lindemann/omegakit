import pytest
from omegaconf import OmegaConf

from omegakit import ConfigValidationError, is_valid, load_config, validate
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
    assert is_valid(cfg, schema=schemas.AppConfig)


def test_validate_returns_nothing_and_leaves_the_config_unchanged(write_yaml):
    cfg = load_config(write_yaml("app.yaml", APP))
    before = OmegaConf.to_container(cfg)
    assert validate(cfg, schema=schemas.AppConfig) is None
    assert OmegaConf.to_container(cfg) == before


def test_validate_builds_nothing():
    validate({"child": {"$class": FAILING}})


def test_validate_checks_root_values_against_the_schema(write_yaml):
    cfg = load_config(write_yaml("app.yaml", APP.replace('"64"', "many")))
    with pytest.raises(ConfigValidationError, match=r"Value .many. of type"):
        validate(cfg, schema=schemas.AppConfig)
    assert not is_valid(cfg, schema=schemas.AppConfig)


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


def test_validate_runs_the_schema_consistency_check():
    with pytest.raises(ConfigValidationError, match="required parameter `z`"):
        validate({"$class": "tests.schemas.MissingParameter"})


def test_validate_root_class_must_match_the_schema():
    with pytest.raises(ConfigValidationError, match="expects AppConfig"):
        validate(_model(), schema=schemas.AppConfig)


def test_validate_rejects_non_dataclass_schemas():
    with pytest.raises(TypeError, match="not a dataclass"):
        validate({}, schema=schemas.Encoder)
