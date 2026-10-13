import math
import os
import sys
from pathlib import Path

import pytest

from omegakit._core.error import OmegaKitBaseException
from omegakit._core.path import (
    PathNotFoundError,
    PathSyntaxError,
    import_path,
)


def test_imports_an_attribute_of_a_module():
    assert import_path("math.sqrt") is math.sqrt
    assert import_path("os.path.join") is os.path.join


@pytest.mark.parametrize("path", ["", "sqrt", ".sqrt", "math.", "math..sqrt"])
def test_malformed_path_is_rejected(path: str):
    with pytest.raises(PathSyntaxError):
        import_path(path)


@pytest.mark.parametrize(
    "path",
    [
        "no_such_module.Name",
        "no_such_package.module.Name",
        "math.no_such_name",
        "math.sqrt.name",
    ],
)
def test_unknown_target_is_not_found(path: str):
    with pytest.raises(PathNotFoundError):
        import_path(path)


def test_missing_dependency_of_the_module_passes_through(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    (tmp_path / "needs_dependency.py").write_text("import no_such_dependency\n")
    monkeypatch.syspath_prepend(tmp_path)
    monkeypatch.delitem(sys.modules, "needs_dependency", raising=False)
    with pytest.raises(ModuleNotFoundError) as error_info:
        import_path("needs_dependency.Name")
    assert not isinstance(error_info.value, OmegaKitBaseException)


@pytest.mark.parametrize(
    ("error_type", "builtin_type"),
    [(PathSyntaxError, ValueError), (PathNotFoundError, ImportError)],
)
def test_errors_are_also_builtin_errors(
    error_type: type[Exception], builtin_type: type[Exception]
):
    assert issubclass(error_type, OmegaKitBaseException)
    assert issubclass(error_type, builtin_type)
