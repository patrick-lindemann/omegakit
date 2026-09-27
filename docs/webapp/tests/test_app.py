from webapp import App
from webapp.db import SQLite


def test_app_uses_an_in_memory_database(app: App) -> None:
    assert isinstance(app.database, SQLite)
    assert app.database.url == "sqlite://"
