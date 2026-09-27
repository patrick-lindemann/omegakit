from pathlib import Path

from omegakit import CLASS_KEY, META_KEY, load_config, walk

configs = Path(__file__).parents[2] / "webapp" / "configs"

config = load_config(configs / "app.yaml", overrides=["server.port=9000"])
print(config.server.port)
print(config.database[CLASS_KEY])

config = load_config(configs / "app.yaml", keep_meta=True)
for node in walk(config):
    if META_KEY in node:
        print(node[CLASS_KEY], node[META_KEY].owner)
