import itertools
import tempfile
from pathlib import Path

import torch
from omegaconf import OmegaConf
from project import Experiment, train

from omegakit import PARTIAL_KEY, instantiate, load_config, make_node

experiments = Path(__file__).parents[2] / "example" / "configs" / "experiments"
runs = Path(tempfile.mkdtemp())
optimizers = {
    "sgd": make_node(torch.optim.SGD, lr=0.1, momentum=0.9),
    "adam": make_node(torch.optim.Adam, lr=0.01),
}

for hidden, (name, optimizer), seed in itertools.product(
    [8, 32], optimizers.items(), [0, 1]
):
    overrides = [
        f"name=mlp{hidden}-{name}",
        f"model.hidden={hidden}",
        f"seed={seed}",
        f"run_dir={runs}/${{name}}/seed${{seed}}",
    ]
    config = load_config(experiments / "mlp.yaml", overrides=overrides)
    config.optimizer = {**optimizer, PARTIAL_KEY: True}

    torch.manual_seed(config.seed)
    experiment = instantiate(config, schema=Experiment)
    experiment.run_dir.mkdir(parents=True)
    OmegaConf.save(config, experiment.run_dir / "config.yaml")

    loss = train(experiment)
    print(experiment.run_dir.relative_to(runs), f"{loss:.3f}")
