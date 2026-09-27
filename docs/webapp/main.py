import sys
from pathlib import Path

from omegaconf import OmegaConf
from webapp import App

from omegakit import instantiate, load_config, mask_secrets

# Overrides from the command line, such as `server.port=9000`.
config = load_config(
    Path(__file__).parent / "configs" / "app.yaml", overrides=sys.argv[1:]
)
print(OmegaConf.to_yaml(mask_secrets(config)))

app = instantiate(config, App)
print(
    f"serving on {app.server.host}:{app.server.port} with {app.server.workers} workers"
)
print(f"database: {type(app.database).__name__} {app.database.url}")
if app.replica is not None:
    print(f"replica: {type(app.replica).__name__} {app.replica.url}")
print(f"cache: {type(app.cache).__name__}, {app.cache.ttl_seconds} s")
for name, job in app.jobs.items():
    print(f"job {name}, every {job.every}: {job.handler()}")
