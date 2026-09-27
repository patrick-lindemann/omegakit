import random
import sys

from curvefit import Experiment
from omegaconf import OmegaConf

from omegakit import instantiate, load_config

# An experiment file, then overrides such as `model.degree=5`.
experiment_file, *overrides = sys.argv[1:]
config = load_config(experiment_file, overrides=overrides)

# Constructors draw random initial weights, so seed before building.
random.seed(config.seed)
experiment = instantiate(config, schema=Experiment)

run_dir = experiment.run_dir
run_dir.mkdir(parents=True)
OmegaConf.save(config, run_dir / "config.yaml")
(run_dir / "overrides.txt").write_text("".join(f"{o}\n" for o in overrides))

model = experiment.model
loss = experiment.trainer.fit(
    model,
    experiment.optimizer(model.parameters()),
    experiment.data.train,
    experiment.data.validation,
    experiment.tracker,
)
xs, ys = experiment.data.test.samples()
predictions = model.predict(xs)
print(f"{experiment.name}: train loss {loss:.4f}")
for name, metric in experiment.metrics.items():
    print(f"test {name}: {metric(predictions, ys):.4f}")
