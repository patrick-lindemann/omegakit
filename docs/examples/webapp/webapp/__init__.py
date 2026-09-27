from dataclasses import dataclass, field
from typing import Any, Self, override

from omegakit import Configurable, instantiate, make_node

from .cache import Cache, MemoryCache
from .db import Database
from .jobs import Job
from .server import Server


@dataclass
class AppConfig:
    server: Server
    database: Database
    replica: Database | None = None
    cache: Cache | None = None
    jobs: dict[str, Job] = field(default_factory=dict)
    log_dir: str = "logs"


class App(Configurable[AppConfig]):
    def __init__(
        self,
        server: Server,
        database: Database,
        replica: Database | None,
        cache: Cache,
        jobs: dict[str, Job],
        log_dir: str,
    ) -> None:
        self.server = server
        self.database = database
        self.replica = replica
        self.cache = cache
        self.jobs = jobs
        self.log_dir = log_dir

    @classmethod
    @override
    def from_config(cls, config: AppConfig, **kwargs: Any) -> Self:
        # Without a configured cache, the app keeps one in memory.
        cache = config.cache or instantiate(
            make_node(MemoryCache, url="memory://", ttl="10m"), Cache
        )
        return cls(
            config.server,
            config.database,
            config.replica,
            cache,
            config.jobs,
            config.log_dir,
        )
