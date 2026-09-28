from pathlib import Path

from project import Experiment

from omegakit import ConfigValidationError, instantiate, load_config, prepare

experiments = Path(__file__).parents[2] / "example" / "configs" / "experiments"
config = load_config(experiments / "mlp.yaml")

experiment = instantiate(config, schema=Experiment)
print(type(experiment.model).__name__, experiment.loss.__name__)
optimizer = experiment.optimizer(experiment.model.parameters())
print(type(optimizer).__name__, optimizer.param_groups[0]["lr"])
optimizer = experiment.optimizer(experiment.model.parameters(), lr=0.1)
print(optimizer.param_groups[0]["lr"])

make_model = prepare(config.model)
print(sum(p.numel() for p in make_model(hidden=8).parameters()))

try:
    instantiate(
        config,
        schema=Experiment,
        overrides=["model.$class=subprocess.Popen"],
        allowed_modules=["project", "torch.nn", "torch.optim"],
    )
except ConfigValidationError as error:
    print(error)
