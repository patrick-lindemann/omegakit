from omegakit import load_config

config = load_config("wide.yaml")
print("config.model.hidden:", config.model.hidden)
print("config.model.layers:", config.model.layers)
print("config.optimizer.lr:", config.optimizer.lr)
print("config.epochs:", config.epochs)

config = load_config("sweep.yaml")
print("config.quick.seeds:", config.quick.seeds)
print("config.quick.hidden:", config.quick.hidden)
