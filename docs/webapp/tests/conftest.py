from pathlib import Path

import pytest
from webapp import App

from omegakit import instantiate, load_config

CONFIGS = Path(__file__).parents[1] / "configs"


@pytest.fixture
def app() -> App:
    # Tests get a fresh in-memory database instead of the configured one.
    config = load_config(
        CONFIGS / "app.yaml",
        overrides={"database": {"$class": "webapp.db.SQLite", "url": "sqlite://"}},
    )
    return instantiate(config, schema=App)
