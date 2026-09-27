from dataclasses import dataclass

from omegakit import Configurable


@dataclass
class DatabaseConfig:
    url: str
    pool_size: int = 5


class Database(Configurable[DatabaseConfig]):
    def __init__(self, url: str, pool_size: int) -> None:
        # Stores its settings and connects to nothing, so every config builds.
        self.url = url
        self.pool_size = pool_size


class Postgres(Database):
    pass


class SQLite(Database):
    pass
