from omegakit import META_KEY, load_config, walk

config = load_config("experiment.yaml")
print("config:", config)

config = load_config("experiment.yaml", keep_meta=True)
print("config.$meta.title:", config[META_KEY].title)
print("config.$meta.version:", config[META_KEY].version)
for node in walk(config):
    if META_KEY in node:
        print("description:", node[META_KEY].description)
