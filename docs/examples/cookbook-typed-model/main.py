from pathlib import Path

from model import ConvEncoder, MlpEncoder, Model

from omegakit import ConfigValidationError, instantiate, load_config, validate

path = Path(__file__).parent / "app.yaml"

config = load_config(path)
validate(config)
model = instantiate(config.model, Model)
assert isinstance(model.encoder, ConvEncoder)
assert (model.encoder.channels, model.encoder.kernel) == (16, 5)

# The encoder is chosen by one override; each encoder is checked by its own schema.
config = load_config(path, overrides=["encoder_choice=mlp"])
model = instantiate(config.model, Model)
assert isinstance(model.encoder, MlpEncoder)
assert model.encoder.hidden == [128, 64]

# `validate` finds mistakes before anything is built.
config = load_config(path, overrides=["encoders.conv.kernel=4"])
try:
    validate(config)
except ConfigValidationError as error:
    assert "encoders.conv.kernel" in str(error)
else:
    raise AssertionError("an invalid kernel must fail")
