from pathlib import Path

from omegakit import load_config

here = Path(__file__).parent

config = load_config(here / "wide.yaml")
print(config.model.hidden, config.model.layers, config.optimizer.lr, config.epochs)

config = load_config(here / "sweep.yaml")
print(config.quick.seeds, config.quick.hidden)
