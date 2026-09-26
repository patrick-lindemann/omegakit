import json
import subprocess
import sys

from omegakit import generate_json_schema
from omegakit.cli import main
from tests import schemas

# Contracts: §12 Editor schemas.


def test_cli_json_schema_prints_the_schema(capsys):
    main(["json-schema", "tests.schemas.AppConfig"])
    assert json.loads(capsys.readouterr().out) == generate_json_schema(
        schemas.AppConfig
    )


def test_cli_json_schema_writes_the_output_file(tmp_path):
    output = tmp_path / "app.schema.json"
    main(["json-schema", "tests.schemas.AppConfig", "-o", str(output)])
    assert json.loads(output.read_text()) == generate_json_schema(schemas.AppConfig)


def test_cli_runs_as_a_module_without_warnings(tmp_path):
    output = tmp_path / "model.schema.json"
    subprocess.run(
        [
            sys.executable,
            "-W",
            "error",
            "-m",
            "omegakit",
            "json-schema",
            "tests.schemas.TypedEncoder",
            "-o",
            str(output),
        ],
        check=True,
    )
    assert json.loads(output.read_text()) == generate_json_schema(schemas.TypedEncoder)
