from pathlib import Path

from models import Activation, Model, Schedule

from omegakit import ConfigValidationError, instantiate, load_config

path = Path(__file__).parent / "model.yaml"
model = instantiate(load_config(path), Model)

# An enum member by value or by name; a fixed-length tuple.
assert model.activation is Activation.GELU
assert model.kernel == (5, 3)
# A union with a dataclass: a mapping builds the dataclass, a number stays a number.
assert model.schedule == Schedule(warmup=100)
assert instantiate(load_config(path, overrides=["schedule=0.5"]), Model).schedule == 0.5
# A list of objects: every item is built and checked.
assert [layer.width for layer in model.layers] == [64, 32]

try:
    instantiate(load_config(path, overrides=["kernel=[3]"]))
except ConfigValidationError as error:
    assert "`kernel` expects a list of 2 items" in str(error)
else:
    raise AssertionError("a kernel of the wrong length must fail")

# `init=False` fields are computed by the dataclass, so a config cannot set them.
try:
    instantiate(load_config(path, overrides=["steps=5"]))
except ConfigValidationError as error:
    assert "'steps'" in str(error)
else:
    raise AssertionError("`steps` must not be configurable")
