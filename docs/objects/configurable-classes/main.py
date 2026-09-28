from project import MLP

from omegakit import check_schema, instantiate, make_node

config = {"$class": "project.MLP", "hidden": "64", "activation": "relu"}
model = instantiate(config)
print(type(model).__name__, model.net)

model = instantiate(make_node(MLP, hidden=8, layers=1))
print(len(model.net))

check_schema(MLP)
