from curvefit.trainer import Trainer

from omegakit import instantiate, make_node

config = {"$class": "curvefit.trainer.Trainer", "epochs": "50", "schedule": "cosine"}
trainer = instantiate(config)
print(type(trainer).__name__, trainer.epochs)

trainer = instantiate(make_node(Trainer, epochs=10))
print(type(trainer).__name__, trainer.epochs)
