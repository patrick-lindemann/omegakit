from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from omegakit import Configurable


@dataclass
class JobConfig:
    handler: Any
    every: str = "1h"
    retries: int = 3


class Job(Configurable[JobConfig]):
    def __init__(self, handler: Callable[[], str], every: str, retries: int) -> None:
        self.handler = handler
        self.every = every
        self.retries = retries


def send_digest(subject: str = "Your weekly digest") -> str:
    return f"sent {subject!r}"


def purge_sessions() -> str:
    return "purged expired sessions"
