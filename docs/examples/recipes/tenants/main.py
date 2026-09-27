from pathlib import Path

from omegaconf import OmegaConf
from webapp import App

from omegakit import instantiate, load_config

here = Path(__file__).parent
configs = here.parents[1] / "webapp" / "configs"

tenants = OmegaConf.to_container(OmegaConf.load(here / "tenants.yaml"))
assert isinstance(tenants, dict)
for name, overrides in tenants.items():
    config = load_config(
        configs / "app.yaml", overrides={**overrides, "log_dir": f"logs/{name}"}
    )
    app = instantiate(config, App)
    print(
        name, app.server.port, app.server.workers, app.database.pool_size, app.log_dir
    )
