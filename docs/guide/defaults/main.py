from omegakit import load_config

config = load_config("experiment.yaml")
print("config.data.train:", config.data.train)
print("config.data.validation:", config.data.validation)
print("config.data.test:", config.data.test)
