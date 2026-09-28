import sys

import torch
from omegaconf import OmegaConf
from project import Experiment, train

from omegakit import instantiate, load_config

# An experiment file, then overrides such as `model.hidden=64`.
experiment_file, *overrides = sys.argv[1:]
config = load_config(experiment_file, overrides=overrides)

# The model draws random initial weights, so seed before building.
torch.manual_seed(config.seed)
experiment = instantiate(config, schema=Experiment)

run_dir = experiment.run_dir
run_dir.mkdir(parents=True)
OmegaConf.save(config, run_dir / "config.yaml")
(run_dir / "overrides.txt").write_text("".join(f"{o}\n" for o in overrides))

loss = train(experiment)
torch.save(experiment.model.state_dict(), run_dir / "model.pt")
print(f"{experiment.name}: test loss {loss:.3f}")
