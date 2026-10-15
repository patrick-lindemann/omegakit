from experiment import Experiment

from omegakit import ConfigValidationError, instantiate, load_config, prepare

config = load_config("experiment.yaml")
experiment = instantiate(config, Experiment)
print("model:", experiment.model)
print("loss:", experiment.loss.__name__)
print("epochs:", repr(experiment.epochs), "batch_size:", experiment.batch_size)

optimizer = experiment.optimizer(experiment.model.parameters())
print("optimizer:", type(optimizer).__name__, optimizer.defaults["lr"])
optimizer = experiment.optimizer(experiment.model.parameters(), lr=0.01)
print("optimizer:", type(optimizer).__name__, optimizer.defaults["lr"])

make_experiment = prepare(config, Experiment)
print("epochs:", make_experiment(epochs=5).epochs)

try:
    instantiate(config.loss)
except ConfigValidationError as error:
    print(f"{type(error).__name__}:", error)
