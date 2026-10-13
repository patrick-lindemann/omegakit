import sys
from pathlib import Path
from types import ModuleType

import pytest


@pytest.fixture
def targets(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.syspath_prepend(Path(__file__).parent / "targets")
    monkeypatch.delitem(sys.modules, "config_targets", raising=False)
    import config_targets  # pyright: ignore[reportMissingImports]

    return config_targets
