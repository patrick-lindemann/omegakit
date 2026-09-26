import contextlib
import io
import os
from pathlib import Path

from omegakit._cli import main

# The same as running `omegakit ...` in this directory.
os.chdir(Path(__file__).parent)


def run(*arguments: str) -> tuple[int, str]:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        try:
            main(list(arguments))
        except SystemExit as error:
            return int(error.code or 0), output.getvalue()
    return 0, output.getvalue()


# `show` prints the assembled config; `--resolve` fills in interpolations.
assert run("show", "app.yaml", "server.host=example.com", "--resolve") == (
    0,
    "server:\n  port: 8080\n  host: example.com\n  url: http://example.com:8080\n",
)

# `check` validates; `server.host` is still `???`.
code, output = run("check", "app.yaml")
assert code == 1
assert output.startswith(
    "app.yaml: ConfigValidationError: Cannot resolve `server.host`"
)
assert run("check", "app.yaml", "server.host=example.com") == (0, "")

# Library files keep open slots on purpose.
assert run("check", "server.yaml", "--allow-missing") == (0, "")
