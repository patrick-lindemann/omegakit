import json
import subprocess
import sys

import pytest

from omegakit import generate_json_schema
from omegakit._cli import main
from tests import schemas

# Contracts: §12 Editor schemas, §13 Command line.


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


MODEL = "model:\n  $class: tests.schemas.Model\n  depth: 2\n"


def _exit_code(arguments: list[str]) -> int:
    with pytest.raises(SystemExit) as info:
        main(arguments)
    return int(info.value.code or 0)


def test_cli_check_accepts_valid_files(write_yaml, capsys):
    main(
        ["check", str(write_yaml("a.yaml", MODEL)), str(write_yaml("b.yaml", "x: 1\n"))]
    )
    assert capsys.readouterr().out == ""


def test_cli_check_reports_every_invalid_file(write_yaml, capsys):
    good = write_yaml("good.yaml", MODEL)
    bad = write_yaml("bad.yaml", MODEL.replace("2", "deep"))
    broken = write_yaml("broken.yaml", "a: ~import missing.yaml\n")
    assert _exit_code(["check", str(bad), str(good), str(broken)]) == 1
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith(f"{bad}: ConfigValidationError: ")
    assert "`model.depth`" in lines[0]
    assert lines[1].startswith(f"{broken}: ConfigValidationError")
    assert len(lines) == 2


def test_cli_check_applies_overrides_in_any_position(write_yaml):
    path = write_yaml("a.yaml", "model:\n  $class: tests.schemas.Model\n  depth: ???\n")
    assert _exit_code(["check", str(path)]) == 1
    main(["check", "model.depth=3", str(path)])


def test_cli_check_allow_missing(write_yaml):
    path = write_yaml("lib.yaml", "name: ???\nurl: http://${name}\n")
    assert _exit_code(["check", str(path)]) == 1
    main(["check", "--allow-missing", str(path)])


def test_cli_check_schema(write_yaml):
    path = write_yaml("frag.yaml", "depth: 2\n")
    main(["check", "--schema", "tests.schemas.Model", str(path)])
    assert _exit_code(["check", "--schema", "tests.schemas.Encoder", str(path)]) == 1
    assert _exit_code(["check", "--schema", "tests.schemas.Nope", str(path)]) == 2


@pytest.mark.parametrize("import_path", ["nodots", "..mod.X"])
def test_cli_check_rejects_a_malformed_schema_path(write_yaml, capsys, import_path):
    path = write_yaml("frag.yaml", "depth: 2\n")
    assert _exit_code(["check", "--schema", import_path, str(path)]) == 2
    assert "is not an import path" in capsys.readouterr().err


def test_cli_check_needs_a_config_file():
    assert _exit_code(["check", "a=1"]) == 2


def test_cli_existing_paths_with_equals_are_files(tmp_path, write_yaml):
    path = write_yaml("lr=0.1/app.yaml", "x: 1\n")
    main(["check", str(path)])
    assert _exit_code(["check", str(tmp_path / "lr=0.2/app.yaml")]) == 1


def test_cli_show_prints_the_assembled_config(write_yaml, capsys):
    write_yaml("base.yaml", "a: 1\nb: 2\n")
    path = write_yaml(
        "app.yaml", "m:\n  $base: ~import base.yaml\n  b: 3\n  $meta: x\n"
    )
    main(["show", str(path), "m.a=5"])
    assert capsys.readouterr().out == "m:\n  b: 3\n  a: 5\n"
    main(["show", str(path), "--keep-meta", "--node", "m"])
    assert "$meta: x" in capsys.readouterr().out


def test_cli_show_resolve_prints_missing_values(write_yaml, capsys):
    path = write_yaml("app.yaml", "name: ???\nurl: http://${name}\nport: ${p}\np: 80\n")
    main(["show", str(path), "--resolve"])
    assert capsys.readouterr().out == "name: ???\nurl: ???\nport: 80\np: 80\n"
    main(["show", str(path), "--node", "p"])
    assert capsys.readouterr().out == "80\n"


def test_cli_show_errors(write_yaml, capsys):
    path = write_yaml("app.yaml", "a: 1\n")
    assert _exit_code(["show", str(path), "--node", "b"]) == 1
    assert _exit_code(["show", str(path.with_name("nope.yaml"))]) == 1
    assert _exit_code(["show", str(path), str(path)]) == 2
    assert "no node `b`" in capsys.readouterr().out


def test_cli_json_schema_check(tmp_path):
    output = tmp_path / "schema.json"
    arguments = ["json-schema", "tests.schemas.TypedEncoder", "-o", str(output)]
    assert _exit_code([*arguments, "--check"]) == 1
    main(arguments)
    main([*arguments, "--check"])
    output.write_text("{}")
    assert _exit_code([*arguments, "--check"]) == 1
    assert _exit_code(["json-schema", "tests.schemas.TypedEncoder", "--check"]) == 2
