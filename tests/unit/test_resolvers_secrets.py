import pytest
from omegaconf import OmegaConf
from omegaconf.errors import InterpolationResolutionError

from omegakit import ConfigValidationError, validate
from omegakit.resolvers import register_resolver
from omegakit.resolvers.secrets import register_secret_resolver


def test_secret_gives_the_environment_variable_it_wraps(monkeypatch):
    monkeypatch.setenv("OMEGAKIT_TEST_TOKEN", "tok-123")
    register_secret_resolver()
    config = OmegaConf.create(
        {"url": "https://h/?token=${secret:${oc.env:OMEGAKIT_TEST_TOKEN}}"}
    )
    assert config.url == "https://h/?token=tok-123"


def test_secret_wraps_any_resolver():
    register_secret_resolver()
    register_resolver("vault", lambda path: f"from-{path}")
    assert OmegaConf.create({"password": "${secret:${vault:db}}"}).password == "from-db"


def test_secret_gives_a_plain_value_as_written():
    register_secret_resolver()
    assert OmegaConf.create({"token": "${secret:TOKEN}"}).token == "TOKEN"


def test_saving_the_unresolved_config_keeps_the_interpolation(monkeypatch):
    monkeypatch.setenv("OMEGAKIT_TEST_TOKEN", "tok-123")
    register_secret_resolver()
    config = OmegaConf.create({"token": "${secret:${oc.env:OMEGAKIT_TEST_TOKEN}}"})
    assert config.token == "tok-123"
    assert OmegaConf.to_yaml(config) == (
        "token: ${secret:${oc.env:OMEGAKIT_TEST_TOKEN}}\n"
    )


def test_secret_fails_as_the_interpolation_it_wraps(monkeypatch):
    monkeypatch.delenv("OMEGAKIT_TEST_TOKEN", raising=False)
    register_secret_resolver()
    config = OmegaConf.create({"token": "${secret:${oc.env:OMEGAKIT_TEST_TOKEN}}"})
    with pytest.raises(InterpolationResolutionError, match="OMEGAKIT_TEST_TOKEN"):
        _ = config.token
    with pytest.raises(ConfigValidationError, match=r"`token`.*OMEGAKIT_TEST_TOKEN"):
        validate(config, allow_missing=True)


def test_secret_replacement_is_explicit():
    register_secret_resolver()
    with pytest.raises(ValueError, match="already registered"):
        register_secret_resolver()
    register_secret_resolver(replace=True)
