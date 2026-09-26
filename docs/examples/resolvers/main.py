import importlib
import importlib.util
from pathlib import Path

from omegaconf import OmegaConf

from omegakit import load_config
from omegakit.resolvers.paths import register_paths_resolver

# Register resolvers once, before loading configs. Registration is global.
register_paths_resolver({"data": Path("/srv/data"), "runs": "runs"})

config = load_config(Path(__file__).parent / "app.yaml")
assert config.train_data == "/srv/data/train"
assert config.checkpoints == "runs/checkpoints"

# Registering the same name again raises unless `replace=True` is passed.
try:
    register_paths_resolver({})
except ValueError as error:
    assert "already registered" in str(error)
else:
    raise AssertionError("registering twice must fail")
register_paths_resolver({"data": "/mnt/data"}, replace=True)

# The Torch resolvers need PyTorch, which is not a dependency of omegakit.
if importlib.util.find_spec("torch") is not None:
    from omegakit.resolvers.torch import register_torch_resolvers

    torch = importlib.import_module("torch")

    register_torch_resolvers()
    config = OmegaConf.create(
        {"dtype": "${dtype:float16}", "cuda": "${cuda_available:}"}
    )
    assert config.dtype is torch.float16
    assert isinstance(config.cuda, bool)
