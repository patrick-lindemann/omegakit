import pytest
from omegaconf import OmegaConf
from omegaconf.errors import InterpolationResolutionError

from omegakit import ConfigValidationError, validate
from omegakit.resolvers.secrets import register_secret_resolver


def test_secret_reads_the_environment_variable(monkeypatch):
    monkeypatch.setenv("OMEGAKIT_TEST_TOKEN", "tok-123")
    register_secret_resolver()
    config = OmegaConf.create({"url": "https://h/?token=${secret:OMEGAKIT_TEST_TOKEN}"})
    assert config.url == "https://h/?token=tok-123"


def test_saving_the_unresolved_config_keeps_the_interpolation(monkeypatch):
    monkeypatch.setenv("OMEGAKIT_TEST_TOKEN", "tok-123")
    register_secret_resolver()
    config = OmegaConf.create({"token": "${secret:OMEGAKIT_TEST_TOKEN}"})
    assert config.token == "tok-123"
    assert OmegaConf.to_yaml(config) == "token: ${secret:OMEGAKIT_TEST_TOKEN}\n"


def test_unset_secret_raises(monkeypatch):
    monkeypatch.delenv("OMEGAKIT_TEST_TOKEN", raising=False)
    register_secret_resolver()
    config = OmegaConf.create({"token": "${secret:OMEGAKIT_TEST_TOKEN}"})
    with pytest.raises(InterpolationResolutionError, match="is not set"):
        _ = config.token
    with pytest.raises(ConfigValidationError, match=r"`token`.*is not set"):
        validate(config, allow_missing=True)


def test_secret_replacement_is_explicit():
    register_secret_resolver()
    with pytest.raises(ValueError, match="already registered"):
        register_secret_resolver()
    register_secret_resolver(replace=True)
