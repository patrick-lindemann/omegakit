from omegakit import load_config

config = load_config("experiment.yaml")
print("config.run_dir:", config.run_dir)
print("config.data.train.seed:", config.data.train.seed)
print("config.data.test.n:", config.data.test.n)

config.seed = 7
print("config.run_dir:", config.run_dir)
print("config.data.train.seed:", config.data.train.seed)
