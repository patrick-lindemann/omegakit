import os
from pathlib import Path

from plain import Database, Postgres, Server, SQLite

from omegakit import instantiate, load_config

here = Path(__file__).parent

# Step 1: load a file and read values.
config = load_config(here / "step1.yaml")
assert config.server.port == 8000

# Step 2: build an object from a node.
config = load_config(here / "step2.yaml")
server = instantiate(config.server, schema=Server)
assert (server.host, server.port) == ("127.0.0.1", 8000)

# Steps 3 and 4: one file per environment, values from outside.
os.environ["APP_ENV"] = "prod"
os.environ["SECRET_KEY"] = "from-the-environment"
config = load_config(here / "configs" / "app.yaml", overrides=["server.port=9000"])
server = instantiate(config.server, schema=Server)
database = instantiate(config.database, schema=Database)
assert (server.host, server.port) == ("0.0.0.0", 9000)
assert server.secret_key == "from-the-environment"
assert isinstance(database, Postgres)

os.environ["APP_ENV"] = "dev"
config = load_config(here / "configs" / "app.yaml")
assert isinstance(instantiate(config.database, schema=Database), SQLite)
