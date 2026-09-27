from pathlib import Path

from omegakit import CLASS_KEY, META_KEY, load_config, walk

experiments = Path(__file__).parents[2] / "curvefit" / "configs" / "experiments"

config = load_config(experiments / "poly3-adam.yaml", overrides=["trainer.epochs=50"])
print(config.trainer.epochs, config.trainer.schedule)
print(config.data.test[CLASS_KEY], config.data.test.n)

config = load_config(experiments / "poly3-adam.yaml", keep_meta=True)
for node in walk(config):
    if META_KEY in node:
        print(node[META_KEY].hypothesis)
