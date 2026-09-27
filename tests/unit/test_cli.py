import json
import subprocess
import sys

import pytest
import yaml

from omegakit import generate_json_schema
from omegakit.cli import main
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


def test_cli_check_counts_a_module_that_exits_as_invalid(
    write_yaml, tmp_path, monkeypatch, capsys
):
    (tmp_path / "exiting_module.py").write_text("import sys\nsys.exit(0)\n")
    monkeypatch.syspath_prepend(tmp_path)
    monkeypatch.delitem(sys.modules, "exiting_module", raising=False)
    exiting = write_yaml("a.yaml", "x:\n  $class: exiting_module.Main\n")
    invalid = write_yaml("b.yaml", MODEL.replace("2", "deep"))
    assert _exit_code(["check", str(exiting), str(invalid)]) == 1
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith(f"{exiting}: SystemExit")
    assert lines[1].startswith(f"{invalid}: ConfigValidationError")


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


@pytest.mark.parametrize("command", ["check", "show"])
def test_cli_import_root(write_yaml, tmp_path, capsys, command):
    write_yaml("outside.yaml", "a: 1\n")
    path = write_yaml("configs/app.yaml", "n: ~import ../outside.yaml\n")
    main([command, str(path)])
    capsys.readouterr()
    root = str(tmp_path / "configs")
    assert _exit_code([command, str(path), "--import-root", root]) == 1
    assert "outside the import root" in capsys.readouterr().out
    missing = str(tmp_path / "missing")
    assert _exit_code([command, str(path), "--import-root", missing]) == 2


def test_cli_check_allow_module(write_yaml, capsys):
    path = write_yaml("a.yaml", MODEL)
    main(["check", str(path), "--allow-module", "other", "--allow-module", "tests"])
    assert _exit_code(["check", str(path), "--allow-module", "other"]) == 1
    assert "allowed_modules" in capsys.readouterr().out


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
    assert yaml.safe_load(capsys.readouterr().out) == {"m": {"a": 5, "b": 3}}
    main(["show", str(path), "--keep-meta", "--node", "m"])
    assert "$meta: x" in capsys.readouterr().out


def test_cli_show_resolve_prints_missing_values(write_yaml, capsys):
    path = write_yaml("app.yaml", "name: ???\nurl: http://${name}\nport: ${p}\np: 80\n")
    main(["show", str(path), "--resolve"])
    assert capsys.readouterr().out == "name: ???\nurl: ???\nport: 80\np: 80\n"
    main(["show", str(path), "--node", "p"])
    assert capsys.readouterr().out == "80\n"


SHOW_NODES = """\
db:
  url: postgres://u:${oc.env:OMEGAKIT_TEST_PASSWORD}@h/db
  empty: null
  host: ???
items:
  - {name: a}
  - {name: b}
alias: ${items}
broken: ${nope}
"""


@pytest.mark.parametrize(
    ("node", "output"),
    [
        ("db.url", "postgres://u:${oc.env:OMEGAKIT_TEST_PASSWORD}@h/db\n"),
        ("db.empty", "null\n"),
        ("db.host", "???\n"),
        ("items.1", "name: b\n"),
        ("items.-1.name", "b\n"),
        ("alias", "${items}\n"),
    ],
)
def test_cli_show_node_is_not_resolved(write_yaml, capsys, monkeypatch, node, output):
    monkeypatch.setenv("OMEGAKIT_TEST_PASSWORD", "hunter2")
    main(["show", str(write_yaml("app.yaml", SHOW_NODES)), "--node", node])
    assert capsys.readouterr().out == output


def test_cli_show_node_through_an_interpolation_needs_resolve(write_yaml, capsys):
    path = write_yaml("app.yaml", SHOW_NODES)
    assert _exit_code(["show", str(path), "--node", "alias.0.name"]) == 1
    message = capsys.readouterr().out
    assert "`alias`" in message
    assert "--resolve" in message
    main(["show", str(path), "--node", "alias.0.name", "--resolve"])
    assert capsys.readouterr().out == "a\n"


def test_cli_show_resolves_only_the_selected_node(write_yaml, capsys):
    path = write_yaml("app.yaml", SHOW_NODES)
    main(["show", str(path), "--node", "db.host", "--resolve"])
    assert capsys.readouterr().out == "???\n"
    main(["show", str(path), "--node", "items", "--resolve"])
    assert capsys.readouterr().out == "- name: a\n- name: b\n"


@pytest.mark.parametrize(
    "arguments",
    [["--resolve"], ["--node", "x", "--resolve"], ["--node", "y.z", "--resolve"]],
)
def test_cli_show_reports_resolution_errors(write_yaml, capsys, arguments):
    path = write_yaml("app.yaml", "x: ${nope:1}\ny: ${nope:2}\n")
    assert _exit_code(["show", str(path), *arguments]) == 1
    assert capsys.readouterr().out.startswith(f"{path}: ")


SECRETS = """\
db:
  password: ${oc.env:OMEGAKIT_TEST_PASSWORD}
  url: postgres://u:${.password}@h/db
  user: ${oc.env:OMEGAKIT_TEST_USER}
tokens:
  api: literal-token
"""


@pytest.mark.parametrize(
    ("arguments", "output"),
    [
        (
            [],
            "db:\n  password: '***'\n  url: postgres://u:${.password}@h/db\n"
            "  user: ${oc.env:OMEGAKIT_TEST_USER}\ntokens:\n  api: '***'\n",
        ),
        (
            ["--resolve"],
            "db:\n  password: '***'\n  url: postgres://u:***@h/db\n  user: app\n"
            "tokens:\n  api: '***'\n",
        ),
        (["--node", "db.url", "--resolve"], "postgres://u:***@h/db\n"),
        (["--node", "db.password"], "***\n"),
        (["--node", "tokens.api"], "***\n"),
        (["--node", "tokens"], "api: '***'\n"),
        (
            ["--node", "db.url", "--resolve", "--show-secrets"],
            "postgres://u:correct-horse@h/db\n",
        ),
    ],
)
def test_cli_show_masks_secrets(write_yaml, capsys, monkeypatch, arguments, output):
    monkeypatch.setenv("OMEGAKIT_TEST_PASSWORD", "correct-horse")
    monkeypatch.setenv("OMEGAKIT_TEST_USER", "app")
    main(["show", str(write_yaml("app.yaml", SECRETS)), *arguments])
    assert capsys.readouterr().out == output


def test_cli_show_errors(write_yaml, capsys):
    path = write_yaml("app.yaml", "a: 1\n")
    assert _exit_code(["show", str(path), "--node", "b"]) == 1
    assert _exit_code(["show", str(path), "--node", "a.b"]) == 1
    assert _exit_code(["show", str(path.with_name("nope.yaml"))]) == 1
    assert _exit_code(["show", str(path), str(path)]) == 2
    assert "no node `b`" in capsys.readouterr().out


@pytest.mark.parametrize(
    "import_path", ["tests.schemas.Nope", "tests.no_such_module.X", "nodots"]
)
def test_cli_json_schema_reports_import_failures(capsys, import_path):
    assert _exit_code(["json-schema", import_path]) == 2
    assert "cannot import" in capsys.readouterr().err


def test_cli_json_schema_check(tmp_path):
    output = tmp_path / "schema.json"
    arguments = ["json-schema", "tests.schemas.TypedEncoder", "-o", str(output)]
    assert _exit_code([*arguments, "--check"]) == 1
    main(arguments)
    main([*arguments, "--check"])
    output.write_text("{}")
    assert _exit_code([*arguments, "--check"]) == 1
    assert _exit_code(["json-schema", "tests.schemas.TypedEncoder", "--check"]) == 2
