from pathlib import Path

from omegakit import load_config

here = Path(__file__).parent
experiments = here.parents[1] / "curvefit" / "configs" / "experiments"

config = load_config(experiments / "linear-sgd.yaml")
print(config.name, config.seed, config.trainer.epochs)
print(config.data.test.n, config.data.test.seed)

config = load_config(here / "sweep.yaml")
print(config.quick.seeds, config.quick.degrees)
