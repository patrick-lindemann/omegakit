from pathlib import Path

from curvefit import Experiment

from omegakit import ConfigValidationError, instantiate, load_config, prepare

experiments = Path(__file__).parents[2] / "curvefit" / "configs" / "experiments"
config = load_config(experiments / "poly3-adam.yaml")

experiment = instantiate(config, schema=Experiment)
print(type(experiment.model).__name__, experiment.metrics["mse"]([1.0], [3.0]))
optimizer = experiment.optimizer(experiment.model.parameters())
print(type(optimizer).__name__, optimizer.param_groups[0]["lr"])
optimizer = experiment.optimizer(experiment.model.parameters(), lr=0.1)
print(optimizer.param_groups[0]["lr"])

make_model = prepare(config.model)
print(make_model(degree=5).degree)

try:
    instantiate(
        config,
        schema=Experiment,
        overrides=["model.$class=subprocess.Popen"],
        allowed_modules=["curvefit"],
    )
except ConfigValidationError as error:
    print(error)
