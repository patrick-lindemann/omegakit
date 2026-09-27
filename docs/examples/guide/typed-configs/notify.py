from dataclasses import dataclass
from typing import Any, override

from omegakit import Configurable


@dataclass
class NotifierConfig:
    url: str


class Notifier(Configurable[NotifierConfig]):
    def __init__(self, url: str) -> None:
        self.url = url

    @classmethod
    @override
    def from_config(cls, config: NotifierConfig, **kwargs: Any) -> "Notifier":
        if config.url.startswith("mailto:"):
            return EmailNotifier(config.url)
        return WebhookNotifier(config.url)


class EmailNotifier(Notifier):
    pass


class WebhookNotifier(Notifier):
    pass
