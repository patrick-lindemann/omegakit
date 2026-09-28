from models import MLP

from omegakit import ConfigValidationError, check_schema, instantiate, make_node

model = instantiate({"$class": "models.MLP", "hidden": "64", "activation": "relu"})
print("model:", model)

try:
    instantiate({"$class": "models.MLP", "hidden": 64, "activation": "gelu"})
except ConfigValidationError as error:
    print("error:", error)

node = make_node(MLP, hidden=8)
print("node:", node)
print("instantiate(node):", instantiate(node))

check_schema(MLP)
