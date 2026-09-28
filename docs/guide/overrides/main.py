from pathlib import Path

from omegakit import load_config

here = Path(__file__).parent

config = load_config(
    here / "experiment.yaml", overrides=["model.hidden=64", "epochs=50"]
)
print(config.model.hidden, config.epochs)

config = load_config(here / "experiment.yaml", overrides={"optimizer": {"lr": 0.001}})
print(config.optimizer.lr, config.optimizer.momentum)
