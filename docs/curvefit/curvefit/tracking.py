import json
import urllib.request
from pathlib import Path


class Tracker:
    """Writes metrics to the run directory, and posts them to a server if given."""

    run_dir: Path
    url: str | None

    def __init__(self, run_dir: Path, url: str | None = None) -> None:
        self.run_dir = Path(run_dir)
        self.url = url

    def log(self, step: int, **metrics: float) -> None:
        record = json.dumps({"step": step, **metrics})
        with (self.run_dir / "metrics.jsonl").open("a") as file:
            file.write(record + "\n")
        if self.url is not None:
            request = urllib.request.Request(
                self.url,
                data=record.encode(),
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(request, timeout=10).close()
