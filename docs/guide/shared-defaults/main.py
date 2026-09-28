from pathlib import Path

from omegakit import CLASS_KEY, load_config

experiments = Path(__file__).parents[2] / "curvefit" / "configs" / "experiments"

data = load_config(experiments / "linear-sgd.yaml").data
for name, split in data.items():
    print(name, split[CLASS_KEY], split.noise, split.n, split.seed)
