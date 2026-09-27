import random
import sys
from pathlib import Path

import torch
from curvefit import Experiment

from omegakit import instantiate, load_config
from omegakit.resolvers.torch import register_torch_resolvers

register_torch_resolvers()
config = load_config(Path(__file__).parent / "experiment.yaml", overrides=sys.argv[1:])

random.seed(config.seed)
torch.manual_seed(config.seed)
experiment = instantiate(config, schema=Experiment)
Path(experiment.run_dir).mkdir(parents=True)

model = experiment.model
optimizer = experiment.optimizer(model.parameters())
loss = experiment.trainer.fit(
    model,
    optimizer,
    experiment.data.train,
    experiment.data.validation,
    experiment.tracker,
)
xs, ys = experiment.data.test.samples()
predictions = model.predict(xs)
print(f"{experiment.name}: {type(optimizer).__qualname__}, {model.dtype}")
print(f"train loss {loss:.2f}")
for name, metric in experiment.metrics.items():
    print(f"test {name}: {metric(predictions, ys):.2f}")
