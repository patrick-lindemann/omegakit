from pathlib import Path

from omegakit import instantiate, load_config

path = Path(__file__).parent / "app.yaml"

# `$meta` is stripped on load by default.
config = load_config(path)
assert "$meta" not in config
assert "$meta" not in config.exporter

# `keep_meta=True` keeps it, for tools that read it.
config = load_config(path, keep_meta=True)
assert config["$meta"].description == "Nightly export job"
assert config.exporter["$meta"].owner == "data-team"

# Instantiation never passes `$meta` on.
assert instantiate(config.exporter) == {"format": "parquet"}
