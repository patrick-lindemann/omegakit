from pathlib import Path

from omegakit import load_config

experiments = Path(__file__).parents[2] / "curvefit" / "configs" / "experiments"

overrides = ["model.degree=5", "trainer.epochs=50"]
config = load_config(experiments / "poly3-adam.yaml", overrides=overrides)
print(config.model.degree, config.trainer.epochs)

config = load_config(
    experiments / "poly3-adam.yaml", overrides={"optimizer": {"lr": 0.01}}
)
print(config.optimizer.lr, config.optimizer["$class"])
