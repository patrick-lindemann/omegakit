from dataclasses import dataclass
from typing import Any, Self, override

from omegakit import Configurable

UNITS = {"s": 1, "m": 60, "h": 3600}


@dataclass
class CacheConfig:
    url: str
    ttl: str = "10m"


class Cache(Configurable[CacheConfig]):
    def __init__(self, url: str, ttl_seconds: int) -> None:
        self.url = url
        self.ttl_seconds = ttl_seconds

    @classmethod
    @override
    def from_config(cls, config: CacheConfig, **kwargs: Any) -> Self:
        ttl_seconds = int(config.ttl[:-1]) * UNITS[config.ttl[-1]]
        return cls(config.url, ttl_seconds, **kwargs)


class MemoryCache(Cache):
    pass


class RedisCache(Cache):
    pass
