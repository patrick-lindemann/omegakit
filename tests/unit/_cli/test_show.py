from pathlib import Path

import pytest
import yaml

from omegakit.__main__ import main

_NODES = """\
db:
  url: postgres://u:${oc.env:OMEGAKIT_TEST_PASSWORD}@h/db
  empty: null
  host: ???
items:
  - {name: a}
  - {name: b}
alias: ${items}
"""

_SECRETS = """\
db:
  password: ${secret:${oc.env:OMEGAKIT_TEST_PASSWORD}}
  url: postgres://u:${.password}@h/db
  user: ${oc.env:OMEGAKIT_TEST_USER}
"""


def _exit_code(arguments: list[str]) -> int:
    with pytest.raises(SystemExit) as info:
        main(arguments)
    return int(info.value.code or 0)


def test_prints_the_assembled_config(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    (tmp_path / "base.yaml").write_text("a: 1\nb: 2\n")
    path = tmp_path / "app.yaml"
    path.write_text("m:\n  $base: ~include base.yaml\n  b: 3\n  $meta: x\n")
    main(["show", str(path), "--overrides", "m.a=5", "m.b=6"])
    assert yaml.safe_load(capsys.readouterr().out) == {"m": {"a": 5, "b": 6}}
    main(["show", str(path), "--keep-meta", "--node", "m"])
    assert "$meta: x" in capsys.readouterr().out


def test_prints_interpolations_unless_resolved(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    path = tmp_path / "app.yaml"
    path.write_text("name: ???\nport: ${p}\np: 80\n")
    main(["show", str(path)])
    assert capsys.readouterr().out == "name: ???\nport: ${p}\np: 80\n"
    main(["show", str(path), "--resolve"])
    assert capsys.readouterr().out == "name: ???\nport: 80\np: 80\n"


@pytest.mark.parametrize(
    ("node", "output"),
    [
        ("db.url", "postgres://u:hunter2@h/db\n"),
        ("db.empty", "null\n"),
        ("items[1].name", "b\n"),
        ("alias", "- name: a\n- name: b\n"),
        ("alias.0.name", "a\n"),
    ],
)
def test_node_selects_as_omegaconf_does(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    node: str,
    output: str,
):
    monkeypatch.setenv("OMEGAKIT_TEST_PASSWORD", "hunter2")
    path = tmp_path / "app.yaml"
    path.write_text(_NODES)
    main(["show", str(path), "--node", node])
    assert capsys.readouterr().out == output


@pytest.mark.parametrize("node", ["db.host", "db.nope"])
def test_node_that_is_missing_is_no_node(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], node: str
):
    path = tmp_path / "app.yaml"
    path.write_text(_NODES)
    assert _exit_code(["show", str(path), "--node", node]) == 1
    assert capsys.readouterr().err == f"{path}: no node `{node}`\n"


@pytest.mark.parametrize(
    "arguments",
    [["--resolve"], ["--node", "x"], ["--node", "y", "--resolve"]],
)
def test_reports_a_value_that_cannot_be_resolved(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], arguments: list[str]
):
    path = tmp_path / "app.yaml"
    path.write_text("x: ${nope:1}\ny: {z: '${nope:2}'}\n")
    assert _exit_code(["show", str(path), *arguments]) == 1
    assert capsys.readouterr().err.startswith(f"{path}: ")


def test_reports_a_file_that_cannot_be_loaded(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    path = tmp_path / "missing.yaml"
    assert _exit_code(["show", str(path)]) == 1
    assert capsys.readouterr().err.startswith(f"{path}: ConfigFileNotFoundError: ")


@pytest.mark.parametrize(
    ("arguments", "output"),
    [
        (
            ["--resolve"],
            "db:\n  password: '***'\n  url: postgres://u:***@h/db\n  user: app\n",
        ),
        (["--node", "db.url"], "postgres://u:***@h/db\n"),
        (["--node", "db.password"], "***\n"),
        (["--node", "db.url", "--show-secrets"], "postgres://u:correct-horse@h/db\n"),
    ],
)
def test_masks_secret_values(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    arguments: list[str],
    output: str,
):
    monkeypatch.setenv("OMEGAKIT_TEST_PASSWORD", "correct-horse")
    monkeypatch.setenv("OMEGAKIT_TEST_USER", "app")
    path = tmp_path / "app.yaml"
    path.write_text(_SECRETS)
    main(["show", str(path), *arguments])
    assert capsys.readouterr().out == output


def test_include_root_limits_the_includes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    (tmp_path / "configs").mkdir()
    (tmp_path / "outside.yaml").write_text("a: 1\n")
    path = tmp_path / "configs/app.yaml"
    path.write_text("n: ~include ../outside.yaml\n")
    main(["show", str(path)])
    capsys.readouterr()
    root = str(tmp_path / "configs")
    assert _exit_code(["show", str(path), "--include-root", root]) == 1
    assert "outside the include root" in capsys.readouterr().err
    missing = str(tmp_path / "missing")
    assert _exit_code(["show", str(path), "--include-root", missing]) == 2
