import numpy

from omegakit import load_config
from omegakit.resolvers.numpy import register_numpy_resolvers

register_numpy_resolvers()
config = load_config("arrays.yaml")
print("config.dtype:", repr(config.dtype))
print("config.labels_dtype:", repr(config.labels_dtype))

inputs = numpy.zeros(3, dtype=config.dtype)
print("inputs.dtype:", inputs.dtype)
