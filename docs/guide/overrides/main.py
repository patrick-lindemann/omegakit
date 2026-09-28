from omegakit import load_config

config = load_config("experiment.yaml", overrides=["model.hidden=64", "epochs=50"])
print("config.model.hidden:", config.model.hidden)
print("config.epochs:", config.epochs)

config = load_config("experiment.yaml", overrides={"optimizer": {"lr": 0.001}})
print("config.optimizer.lr:", config.optimizer.lr)
print("config.optimizer.momentum:", config.optimizer.momentum)
