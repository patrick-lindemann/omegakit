import subprocess
import sys
from types import ModuleType

import omegakit.resolvers


def test_import_has_no_side_effects():
    subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys
import omegakit
import omegakit.resolvers.torch
from omegaconf import OmegaConf
assert 'torch' not in sys.modules
assert 'dotenv' not in sys.modules
assert 'graspdiff' not in sys.modules
assert not any(OmegaConf.has_resolver(n) for n in ('paths', 'dtype', 'cuda_available'))
""",
        ],
        check=True,
    )


def test_resolvers_package_exports_nothing():
    exports = [
        name
        for name, value in vars(omegakit.resolvers).items()
        if not name.startswith("_") and not isinstance(value, ModuleType)
    ]
    assert exports == []
