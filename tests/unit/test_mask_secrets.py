from typing import cast

import pytest
from omegaconf import DictConfig, OmegaConf

from omegakit import ConfigValidationError, mask_secrets


def _masked(yaml: str, **kwargs):
    return mask_secrets(cast(DictConfig, OmegaConf.create(yaml)), **kwargs)


@pytest.mark.parametrize(
    "key",
    [
        "password",
        "db_password",
        "DB_PASSWORD",
        "passwords",
        "secret_key",
        "apiKey",
        "api-key",
        "apikey",
        "AccessKey",
        "private_keys",
        "auth",
        "refresh_token",
        "pad_token",
        "session.cookie",
        "sentry_dsn",
    ],
)
def test_mask_secrets_masks_keys_with_secret_words(key):
    assert _masked(f"{key}: value\n") == {key: "***"}


@pytest.mark.parametrize("key", ["tokenizer", "author", "passage", "keys", "api"])
def test_mask_secrets_keeps_keys_that_only_contain_the_letters(key):
    assert _masked(f"{key}: value\n") == {key: "value"}


def test_mask_secrets_masks_the_subtree_of_a_secret_key():
    masked = _masked("secrets:\n  db: x\n  api: [a, b]\nport: 80\n")
    assert masked == {"secrets": {"db": "***", "api": ["***", "***"]}, "port": 80}


def test_mask_secrets_masks_secret_environment_variables(monkeypatch):
    monkeypatch.setenv("DB_PASSWORD", "hunter2")
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("PWD", "/home/app")
    masked = _masked(
        "a: ${oc.env:DB_PASSWORD}\n"
        "b: ${ oc.env:DB_PASSWORD}\n"
        "c: ${oc.decode:${oc.env:DB_PASSWORD}}\n"
        "env: ${oc.env:APP_ENV}\n"
        "cwd: ${oc.env:PWD}\n"
    )
    assert masked == {
        "a": "***",
        "b": "***",
        "c": "***",
        "env": "prod",
        "cwd": "/home/app",
    }


def test_mask_secrets_replaces_long_secrets_in_other_strings(monkeypatch):
    monkeypatch.setenv("DB_PASSWORD", "correct-horse")
    masked = _masked(
        "db:\n"
        "  password: ${oc.env:DB_PASSWORD}\n"
        "  url: postgres://u:${.password}@h/db\n"
        "server:\n"
        "  secret_key: s3cr3t-value\n"
        "  copy: ${.secret_key}\n"
        "  number: 12345678\n"
    )
    assert masked == {
        "db": {"password": "***", "url": "postgres://u:***@h/db"},
        "server": {"secret_key": "***", "copy": "***", "number": 12345678},
    }


def test_mask_secrets_keeps_short_secrets_elsewhere():
    masked = _masked("password: short\nnote: a short note\n")
    assert masked == {"password": "***", "note": "a short note"}


def test_mask_secrets_masks_non_string_values():
    assert _masked("token: 12345678\nport: 12345678\n") == {
        "token": "***",
        "port": 12345678,
    }


def test_mask_secrets_ignores_an_unset_secret_variable(monkeypatch):
    monkeypatch.delenv("OMEGAKIT_UNSET_PASSWORD", raising=False)
    assert _masked("a: ${oc.env:OMEGAKIT_UNSET_PASSWORD}\n") == {"a": "***"}


def test_mask_secrets_keeps_missing_values():
    assert _masked("password: ???\nname: ???\n") == {"password": "???", "name": "???"}


def test_mask_secrets_adds_keys():
    masked = _masked(
        "session_id: a\nsalt: b\nsession_name: c\nuser_id: d\n",
        keys=["salt", "Session ID"],
    )
    assert masked == {
        "session_id": "***",
        "salt": "***",
        "session_name": "c",
        "user_id": "d",
    }


def test_mask_secrets_reports_other_resolution_errors():
    with pytest.raises(ConfigValidationError, match="`a`"):
        _masked("a: ${nope:1}\n")
