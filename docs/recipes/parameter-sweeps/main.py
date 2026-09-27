import itertools
import random
import tempfile
from pathlib import Path

from curvefit import Experiment
from curvefit.optim import SGD, Adam
from omegaconf import OmegaConf

from omegakit import PARTIAL_KEY, instantiate, load_config, make_node

experiments = Path(__file__).parents[2] / "curvefit" / "configs" / "experiments"
runs = Path(tempfile.mkdtemp())
optimizers = {
    "sgd": make_node(SGD, lr=0.1, momentum=0.9),
    "adam": make_node(Adam, lr=0.05),
}

for degree, (name, optimizer), seed in itertools.product(
    [3, 5], optimizers.items(), [0, 1]
):
    overrides = [
        f"name=poly{degree}-{name}",
        f"model.degree={degree}",
        f"seed={seed}",
        f"run_dir={runs}/${{name}}/seed${{seed}}",
    ]
    config = load_config(experiments / "poly3-adam.yaml", overrides=overrides)
    config.optimizer = {**optimizer, PARTIAL_KEY: True}

    random.seed(config.seed)
    experiment = instantiate(config, schema=Experiment)
    experiment.run_dir.mkdir(parents=True)
    OmegaConf.save(config, experiment.run_dir / "config.yaml")

    model = experiment.model
    experiment.trainer.fit(
        model,
        experiment.optimizer(model.parameters()),
        experiment.data.train,
        experiment.data.validation,
        experiment.tracker,
    )
    xs, ys = experiment.data.test.samples()
    mse = experiment.metrics["mse"](model.predict(xs), ys)
    print(experiment.run_dir.relative_to(runs), f"{mse:.4f}")
