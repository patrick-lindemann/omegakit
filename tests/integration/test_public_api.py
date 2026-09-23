import subprocess
import sys
from types import ModuleType

import omegakit
import omegakit.resolvers

# Contracts: §9 Environment.


def test_public_api_exports():
    assert sorted(omegakit.__all__) == [
        "BASE_KEY",
        "CLASS_KEY",
        "Configurable",
        "DEFAULTS_KEY",
        "IMPORT_KEY",
        "META_KEY",
        "PARTIAL_KEY",
        "REF_KEY",
        "instantiate",
        "load_config",
        "prepare",
        "walk",
    ]
    assert all(hasattr(omegakit, name) for name in omegakit.__all__)


def test_import_has_no_side_effects():
    subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys
import omegakit
import omegakit.resolvers.paths
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
