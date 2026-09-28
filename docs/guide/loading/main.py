from pathlib import Path

from omegakit import META_KEY, load_config, walk

here = Path(__file__).parent

config = load_config(here / "experiment.yaml")
print(type(config).__name__, config.model.hidden, config.optimizer.lr)

config = load_config(here / "annotated.yaml")
print(META_KEY in config)
config = load_config(here / "annotated.yaml", keep_meta=True)
for node in walk(config):
    if META_KEY in node:
        print(node[META_KEY].hypothesis)
