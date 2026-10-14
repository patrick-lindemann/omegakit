import importlib
import sys
from types import ModuleType

import pytest


@pytest.fixture
def targets(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.delitem(sys.modules, "tests.targets", raising=False)
    return importlib.import_module("tests.targets")
