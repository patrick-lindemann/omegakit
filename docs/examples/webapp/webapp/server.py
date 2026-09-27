from dataclasses import dataclass

from omegakit import Configurable


@dataclass(kw_only=True)
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8000
    workers: int = 1
    secret_key: str


class Server(Configurable[ServerConfig]):
    def __init__(self, host: str, port: int, workers: int, secret_key: str) -> None:
        self.host = host
        self.port = port
        self.workers = workers
        self.secret_key = secret_key
