import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from omegakit import (
    Configurable,
    ConfigValidationError,
    instantiate,
    prepare,
    validate,
)
from tests.schemas import Encoder

MODULES = {
    "recorded.py": "IMPORTED = True\n\nclass Thing: ...\n",
    "pkgx/__init__.py": "from .db import Postgres\n",
    "pkgx/db.py": "from subprocess import run\n\nclass Postgres: ...\n",
}


@pytest.fixture(autouse=True)
def modules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name, source in MODULES.items():
        path = tmp_path / name
        path.parent.mkdir(exist_ok=True)
        path.write_text(source)
    monkeypatch.syspath_prepend(tmp_path)
    for name in ("recorded", "pkgx", "pkgx.db"):
        monkeypatch.delitem(sys.modules, name, raising=False)


@dataclass
class HolderConfig:
    anything: Any = None
    encoders: list[Encoder] = field(default_factory=list)
    by_name: dict[str, Encoder] = field(default_factory=dict)


class Holder(Configurable[HolderConfig]):
    def __init__(self, **fields: Any) -> None:
        self.fields = fields


HOLDER = f"{__name__}.Holder"


def _accepted(config: dict[str, Any], allowed_modules: list[str] | None) -> None:
    validate(config, allowed_modules=allowed_modules)
    instantiate(config, allowed_modules=allowed_modules)
    prepare(config, allowed_modules=allowed_modules)


def _rejected(config: dict[str, Any], allowed_modules: list[str], match: str) -> None:
    for check in (validate, instantiate, prepare):
        with pytest.raises(ConfigValidationError, match=match):
            check(config, allowed_modules=allowed_modules)


def test_allowed_modules_never_imports_a_module_that_is_not_allowed():
    config = {"$class": HOLDER, "anything": {"$class": "recorded.Thing"}}
    _rejected(config, ["tests"], r"`\$class: recorded\.Thing` in `anything`")
    assert "recorded" not in sys.modules


def test_allowed_modules_allows_submodules_but_not_lookalike_prefixes():
    _accepted({"$class": HOLDER}, ["tests"])
    _rejected({"$class": HOLDER}, ["test"], "not in `allowed_modules`")


def test_allowed_modules_checks_the_module_an_object_is_defined_in():
    _rejected({"$class": "pkgx.db.run"}, ["pkgx"], "defined in `subprocess`")
    validate({"$class": "pkgx.Postgres"}, allowed_modules=["pkgx"])


@pytest.mark.parametrize(
    "values",
    [
        {"anything": {"$class": "recorded.Thing"}},
        {"anything": [{"x": {"$ref": "recorded.IMPORTED"}}]},
        {"encoders": [{"$class": "recorded.Thing"}]},
        {"by_name": {"a": {"$class": "recorded.Thing"}}},
    ],
)
def test_allowed_modules_covers_nested_nodes(values):
    _rejected({"$class": HOLDER, **values}, ["tests"], "not in `allowed_modules`")
    assert "recorded" not in sys.modules


def test_allowed_modules_none_allows_everything_and_empty_allows_nothing():
    _accepted({"$class": HOLDER, "anything": {"$ref": "recorded.IMPORTED"}}, None)
    _rejected({"$class": HOLDER}, [], "not in `allowed_modules`")


def test_allowed_modules_accepts_any_iterable():
    config = {"$class": HOLDER}
    validate(config, allowed_modules=(name for name in ["tests"]))
    instantiate(config, allowed_modules=(name for name in ["tests"]))


def test_allowed_modules_rejects_a_string():
    for check in (validate, instantiate, prepare):
        with pytest.raises(TypeError, match="not the string"):
            check({"$class": HOLDER}, allowed_modules="tests")
