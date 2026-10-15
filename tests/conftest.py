import importlib
import importlib.util
import sys
from types import ModuleType

import pytest

# Pytest imports a module even when its marker deselects every test in it, so a module
# that imports a library of an optional group is left out where that group is missing.
collect_ignore = [
    file_name
    for file_name, libraries in (
        ("integration/test_guide_examples.py", ("numpy", "torch")),
        ("unit/resolvers/test_numpy.py", ("numpy",)),
        ("unit/resolvers/test_torch.py", ("torch",)),
    )
    if any(importlib.util.find_spec(library) is None for library in libraries)
]


@pytest.fixture
def targets(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.delitem(sys.modules, "tests.targets", raising=False)
    return importlib.import_module("tests.targets")
