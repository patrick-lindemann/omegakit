from models import MLP

from omegakit import ConfigValidationError, instantiate, make_node, prepare

model = instantiate({"$target": "models.MLP", "hidden": "8", "activation": "relu"})
print("model:", model)

try:
    instantiate({"$target": "models.MLP", "hiden": 8})
except ConfigValidationError as error:
    print(f"{type(error).__name__}:", error)

print("node:", make_node(MLP, hidden=4, layers=2))

make_mlp = prepare({"$target": "models.MLP", "activation": "relu"}, MLP)
print("make_mlp(hidden=2):", make_mlp(hidden=2)[0])
try:
    make_mlp(layers=2)
except ConfigValidationError as error:
    print(f"{type(error).__name__}:", error)
