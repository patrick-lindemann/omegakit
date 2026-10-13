import math
import os
import sys
from pathlib import Path

import pytest

from omegakit._core.error import OmegaKitBaseException
from omegakit._core.locate import (
    QualifiedNameNotFoundError,
    QualifiedNameSyntaxError,
    locate,
)


def test_imports_an_attribute_of_a_module():
    assert locate("math.sqrt") is math.sqrt
    assert locate("os.path.join") is os.path.join


@pytest.mark.parametrize("qualified_name", ["", "sqrt", ".sqrt", "math.", "math..sqrt"])
def test_malformed_name_is_rejected(qualified_name: str):
    with pytest.raises(QualifiedNameSyntaxError):
        locate(qualified_name)


@pytest.mark.parametrize(
    "qualified_name",
    [
        "no_such_module.Name",
        "no_such_package.module.Name",
        "math.no_such_name",
        "math.sqrt.name",
    ],
)
def test_unknown_target_is_not_found(qualified_name: str):
    with pytest.raises(QualifiedNameNotFoundError):
        locate(qualified_name)


def test_missing_dependency_of_the_module_passes_through(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    (tmp_path / "needs_dependency.py").write_text("import no_such_dependency\n")
    monkeypatch.syspath_prepend(tmp_path)
    monkeypatch.delitem(sys.modules, "needs_dependency", raising=False)
    with pytest.raises(ModuleNotFoundError) as error_info:
        locate("needs_dependency.Name")
    assert not isinstance(error_info.value, OmegaKitBaseException)


@pytest.mark.parametrize(
    ("error_type", "builtin_type"),
    [(QualifiedNameSyntaxError, ValueError), (QualifiedNameNotFoundError, ImportError)],
)
def test_errors_are_also_builtin_errors(
    error_type: type[Exception], builtin_type: type[Exception]
):
    assert issubclass(error_type, OmegaKitBaseException)
    assert issubclass(error_type, builtin_type)
