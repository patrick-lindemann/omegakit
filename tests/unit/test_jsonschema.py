from typing import Any

import pytest
from jsonschema import Draft7Validator

from omegakit import generate_json_schema
from tests import schemas

# Contracts: §12 Editor schemas.

APP = {
    "seed": 3,
    "training": {
        "model": {"$class": "tests.schemas.Model", "kind": "B", "depth": 2},
        "epochs": 5,
    },
    "callbacks": [{"$class": "tests.schemas.Encoder", "width": 2}],
}


def _errors(schema: type, instance: Any) -> list[str]:
    validator = Draft7Validator(generate_json_schema(schema))
    return [error.message for error in validator.iter_errors(instance)]


def test_json_schema_is_a_valid_draft_7_schema():
    Draft7Validator.check_schema(generate_json_schema(schemas.AppConfig))


def test_json_schema_accepts_a_valid_config():
    assert _errors(schemas.AppConfig, APP) == []


def test_json_schema_requires_nothing():
    assert _errors(schemas.AppConfig, {}) == []
    assert _errors(schemas.AppConfig, {"training": {"model": {}}}) == []


@pytest.mark.parametrize("value", ["${other}", "???", "~import seed.yaml", "a${x}b"])
def test_json_schema_accepts_placeholders_for_scalars(value):
    assert _errors(schemas.AppConfig, {"seed": value}) == []


@pytest.mark.parametrize("value", ["${sections.training}", "~import training.yaml"])
def test_json_schema_accepts_placeholders_for_whole_nodes(value):
    assert _errors(schemas.AppConfig, {"training": value, "data": value}) == []


def test_json_schema_accepts_special_keys():
    config = {
        "$meta": {"author": "me"},
        "$defaults": {"epochs": 1},
        "training": {"$base": "~import base.yaml", "epochs": 2},
    }
    assert _errors(schemas.AppConfig, config) == []


@pytest.mark.parametrize(
    "config", [{"sed": 1}, {"data": {"batch": 1}}, {"training": {"epoch": 1}}]
)
def test_json_schema_rejects_misspelled_keys(config):
    assert _errors(schemas.AppConfig, config)


@pytest.mark.parametrize("config", [{"seed": "three"}, {"seed": 1.5}, {"data": 1}])
def test_json_schema_rejects_wrong_types(config):
    assert _errors(schemas.AppConfig, config)


def test_json_schema_enums_accept_member_names_only():
    assert _errors(schemas.Fields, {"kind": "B"}) == []
    assert _errors(schemas.Fields, {"kind": "beta"})


def test_json_schema_checks_configurable_object_fields_by_class():
    typo = {"training": {"model": {"$class": "tests.schemas.Model", "dpth": 2}}}
    assert _errors(schemas.AppConfig, typo)


def test_json_schema_accepts_any_keys_for_other_classes():
    other = {"training": {"model": {"$class": "tests.schemas.Other", "dpth": 2}}}
    assert _errors(schemas.AppConfig, other) == []
    callbacks = {"callbacks": [{"$class": "tests.schemas.Encoder", "anything": 1}]}
    assert _errors(schemas.AppConfig, callbacks) == []


def test_json_schema_for_a_configurable_describes_a_fragment():
    assert _errors(schemas.TypedEncoder, {"width": 2}) == []
    assert _errors(schemas.TypedEncoder, {"wdth": 2})


def test_json_schema_rejects_classes_without_schema():
    with pytest.raises(TypeError, match="neither a dataclass"):
        generate_json_schema(schemas.Encoder)
