from pathlib import Path

from omegakit import load_config

config = load_config(Path(__file__).parent / "app.yaml")

assert config.encoder.width == 64
assert config.first_layer == "conv"
assert config.decoder.width == 32
assert [stage.width for stage in config.stages] == [32, 16]

# Every import is an independent copy.
config.decoder.width = 1
assert config.stages[0].width == 32
