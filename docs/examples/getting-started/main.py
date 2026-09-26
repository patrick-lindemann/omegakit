from pathlib import Path

from app import Worker

from omegakit import instantiate, load_config

config = load_config(Path(__file__).parent / "app.yaml", overrides=["worker.retries=5"])
worker = instantiate(config.worker, Worker)

assert (worker.name, worker.timeout, worker.retries) == ("indexer", 20, 5)
