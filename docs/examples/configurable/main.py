from pathlib import Path

from pipeline import NamedPipeline, Pipeline, Registry

from omegakit import instantiate, load_config

config = load_config(Path(__file__).parent / "pipelines.yaml")

# The default `from_config` passes the materialized arguments to the constructor.
pipeline = instantiate(config.default, Pipeline)
assert [step.name for step in pipeline.steps] == ["load", "train"]
assert pipeline.retries == 2

# A custom `from_config` translates the config into constructor arguments.
named = instantiate(config.named, NamedPipeline)
assert [step.name for step in named.steps] == ["load", "evaluate"]

# `from_config` is duck-typed: `Configurable` is not required.
assert instantiate(config.registry, Registry).names == ["alpha", "zeta"]
