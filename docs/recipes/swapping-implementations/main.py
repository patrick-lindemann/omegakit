from pathlib import Path

from curvefit import Experiment
from curvefit.data import CsvData
from curvefit.models import Polynomial
from curvefit.optim import Adam

from omegakit import (
    PARTIAL_KEY,
    ConfigValidationError,
    instantiate,
    load_config,
    make_node,
)

curvefit = Path(__file__).parents[2] / "curvefit"
experiment_file = curvefit / "configs" / "experiments" / "linear-sgd.yaml"

config = load_config(experiment_file)
config.data.test = make_node(CsvData, path=str(curvefit / "data" / "measurements.csv"))
config.optimizer = {**make_node(Adam, lr=0.05), PARTIAL_KEY: True}
experiment = instantiate(config, schema=Experiment)
optimizer = experiment.optimizer(experiment.model.parameters())
print(type(experiment.data.test).__name__, type(optimizer).__name__)

config.data.test = make_node(Polynomial, degree=3)
try:
    instantiate(config, schema=Experiment)
except ConfigValidationError as error:
    print(error)

config = load_config(
    experiment_file, overrides=["optimizer.$class=curvefit.optim.Adam"]
)
experiment = instantiate(config, schema=Experiment)
try:
    experiment.optimizer(experiment.model.parameters())
except TypeError as error:
    print(error)
