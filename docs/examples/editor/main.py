import json
from pathlib import Path

from editor_app import AppConfig, Model

from omegakit import generate_json_schema, instantiate, load_config, validate

here = Path(__file__).parent
cfg = load_config(here / "app.yaml")
validate(cfg, schema=AppConfig)
model = instantiate(cfg.training.model, Model)
assert cfg.data.batch_size == 64
assert model.depth == 7
assert model.kind.name == "B"
assert model.encoder is not None
assert model.encoder.width == 8

# The committed editor schemas are what the generator produces.
assert json.loads((here / "app.schema.json").read_text()) == generate_json_schema(
    AppConfig
)
assert json.loads((here / "model.schema.json").read_text()) == generate_json_schema(
    Model
)
