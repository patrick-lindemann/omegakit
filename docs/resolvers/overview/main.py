import math

from omegakit import load_config
from omegakit.resolvers import register_resolver

register_resolver(
    "batches", lambda samples, batch_size: math.ceil(samples / batch_size)
)

config = load_config("train.yaml")
print("config.steps_per_epoch:", config.steps_per_epoch)
