import datetime
import importlib.metadata
import sys
import tempfile
from pathlib import Path

from omegakit import instantiate, load_config, prepare

# Run against an installed omegakit, outside the repository, to check a release.

with tempfile.TemporaryDirectory() as directory:
    Path(directory, "defaults.yaml").write_text("days: 1\nhours: 2\n")
    path = Path(directory, "app.yaml")
    path.write_text(
        "delta:\n"
        "  $base: ~import defaults.yaml\n"
        "  $class: datetime.timedelta\n"
        "  hours: ${hours}\n"
        "hours: ???\n"
    )
    config = load_config(path, overrides=["hours=5"])
    delta = instantiate(config.delta, datetime.timedelta)
    assert delta == datetime.timedelta(days=1, hours=5), delta
    assert prepare(config.delta)(days=3) == datetime.timedelta(days=3, hours=5)

print(
    f"omegakit {importlib.metadata.version('omegakit')} smoke test passed on "
    f"Python {sys.version.split()[0]}"
)
