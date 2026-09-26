from pathlib import Path

from omegaconf import DictConfig

from omegakit import load_config

path = Path(__file__).parent / "app.yaml"

config = load_config(path)
assert isinstance(config, DictConfig)
assert "$meta" not in config
assert config.server["$class"] == "http.server.HTTPServer"

with_meta = load_config(path, keep_meta=True)
assert with_meta["$meta"].owner == "data-team"

plain = load_config(path, keep_targets=False)
assert dict(plain.server) == {"host": "localhost", "port": 8080}
