from omegaconf import DictConfig

from omegakit import META_KEY, load_config, remove_meta, walk

config = load_config("experiment.yaml", keep_meta=True)
config_without_meta = remove_meta(config)
print("config:", config_without_meta)
print("config.$meta.title:", config[META_KEY].title)
print("config.$meta.version:", config[META_KEY].version)
for node in walk(config):
    if isinstance(node, DictConfig) and META_KEY in node:
        print("description:", node[META_KEY].description)
