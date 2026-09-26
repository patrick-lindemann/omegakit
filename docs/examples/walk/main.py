from pathlib import Path

from omegakit import CLASS_KEY, load_config, walk

config = load_config(Path(__file__).parent / "app.yaml")

# Every mapping, parents before children, including mappings inside lists.
targets = [node[CLASS_KEY] for node in walk(config) if CLASS_KEY in node]
assert targets == [
    "myapp.Model",
    "myapp.Encoder",
    "myapp.EarlyStopping",
    "myapp.Checkpoint",
]

# The nodes are the config's own nodes, so a walk can also edit in place.
for node in walk(config):
    if node.get(CLASS_KEY) == "myapp.Checkpoint":
        node.every = 50
assert config.callbacks[1].every == 50
