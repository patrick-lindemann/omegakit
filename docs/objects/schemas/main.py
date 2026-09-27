from pathlib import Path

from notify import Notifier
from webapp import App
from webapp.server import Server

from omegakit import check_schema, instantiate, load_config

check_schema(Server)
server = instantiate(
    {"$class": "webapp.server.Server", "port": "9000", "secret_key": "x"}, schema=Server
)
print(server.port, server.workers)

configs = Path(__file__).parents[2] / "webapp" / "configs"
app = instantiate(load_config(configs / "app.yaml"), schema=App)
print(type(app.cache).__name__, app.cache.ttl_seconds)
app = instantiate(
    load_config(configs / "app.yaml", overrides=["cache=null"]), schema=App
)
print(type(app.cache).__name__)

notifier = instantiate({"$class": "notify.Notifier", "url": "mailto:ops@example.com"})
print(type(notifier).__name__)
assert isinstance(notifier, Notifier)
