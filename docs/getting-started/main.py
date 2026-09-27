import os
import random

from curvefit import Experiment
from curvefit.metrics import mse

from omegakit import ConfigValidationError, instantiate, load_config

config = load_config("experiment.yaml")
model = instantiate(config.model)
print(type(model).__name__, model.degree)

random.seed(0)
model = instantiate(config.model)
data = instantiate(config.data)
optimizer = instantiate(config.optimizer)(model.parameters())

xs, ys = data.samples()
for _ in range(100):
    optimizer.zero_grad()
    model.backward(xs, ys)
    optimizer.step()
print(f"mse {mse(model.predict(xs), ys):.4f}")

os.chdir("../curvefit")

config = load_config("configs/experiments/linear-sgd.yaml")
experiment = instantiate(config, schema=Experiment)
print(experiment.name, type(experiment.model).__name__, experiment.run_dir)

config = load_config("configs/experiments/poly3-adam.yaml", overrides=["model.degre=5"])
try:
    instantiate(config, schema=Experiment)
except ConfigValidationError as error:
    print(error)
