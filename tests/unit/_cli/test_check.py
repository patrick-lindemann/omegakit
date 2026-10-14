import sys
from pathlib import Path
from types import ModuleType

import pytest

from omegakit.__main__ import main

_MODEL = "model:\n  $target: tests.targets.Model\n  depth: 2\n"


def _exit_code(arguments: list[str]) -> int:
    with pytest.raises(SystemExit) as info:
        main(arguments)
    return int(info.value.code or 0)


def test_accepts_valid_files(
    tmp_path: Path, targets: ModuleType, capsys: pytest.CaptureFixture[str]
):
    (tmp_path / "a.yaml").write_text(_MODEL)
    (tmp_path / "b.yaml").write_text("x: 1\n")
    main(["check", str(tmp_path / "a.yaml"), str(tmp_path / "b.yaml")])
    assert capsys.readouterr().out == ""


def test_reports_every_invalid_file(
    tmp_path: Path, targets: ModuleType, capsys: pytest.CaptureFixture[str]
):
    good = tmp_path / "good.yaml"
    good.write_text(_MODEL)
    bad = tmp_path / "bad.yaml"
    bad.write_text(_MODEL.replace("2", "deep"))
    broken = tmp_path / "broken.yaml"
    broken.write_text("a: ~include missing.yaml\n")
    assert _exit_code(["check", str(bad), str(good), str(broken)]) == 1
    lines = capsys.readouterr().err.splitlines()
    assert lines[0].startswith(f"{bad}: ConfigSchemaError: ")
    assert lines[1].startswith(f"{broken}: ConfigFileNotFoundError: ")
    assert len(lines) == 2


def test_counts_a_module_that_exits_as_invalid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    (tmp_path / "exiting_module.py").write_text("import sys\nsys.exit(0)\n")
    monkeypatch.syspath_prepend(tmp_path)
    monkeypatch.delitem(sys.modules, "exiting_module", raising=False)
    path = tmp_path / "a.yaml"
    path.write_text("x:\n  $target: exiting_module.Main\n")
    assert _exit_code(["check", str(path)]) == 1
    assert capsys.readouterr().err.startswith(f"{path}: SystemExit")


def test_applies_overrides(tmp_path: Path, targets: ModuleType):
    path = tmp_path / "a.yaml"
    path.write_text(_MODEL.replace("2", "???"))
    assert _exit_code(["check", str(path)]) == 1
    main(["check", str(path), "--overrides", "model.depth=3"])
    main(["check", "--overrides", "model.depth=3", "--", str(path)])


def test_allow_missing_accepts_what_is_missing(
    tmp_path: Path, targets: ModuleType, capsys: pytest.CaptureFixture[str]
):
    path = tmp_path / "base.yaml"
    path.write_text(
        "name: ???\nrun: runs/${name}\nmodel: {$target: tests.targets.Model}\n"
    )
    schema = tmp_path / "schema.yaml"
    schema.write_text("activation: relu\n")
    for arguments in [
        [str(path)],
        ["--schema", "tests.targets.ModelConfig", str(schema)],
    ]:
        assert _exit_code(["check", *arguments]) == 1
        main(["check", "--allow-missing", *arguments])
    path.write_text("name: ???\nmodel: {$target: tests.targets.Model, depth: deep}\n")
    capsys.readouterr()
    assert _exit_code(["check", "--allow-missing", str(path)]) == 1
    assert capsys.readouterr().err.startswith(f"{path}: ConfigSchemaError: ")


def test_checks_the_root_against_a_schema(tmp_path: Path, targets: ModuleType):
    path = tmp_path / "a.yaml"
    path.write_text("depth: 2\n")
    main(["check", "--schema", "tests.targets.ModelConfig", str(path)])
    path.write_text("depth: deep\n")
    assert (
        _exit_code(["check", "--schema", "tests.targets.ModelConfig", str(path)]) == 1
    )


@pytest.mark.parametrize(
    ("schema", "message"),
    [
        ("builtins.len", "--schema builtins.len is not a class"),
        ("tests.targets.Nope", "cannot import --schema"),
        ("nodots", "cannot import --schema"),
    ],
)
def test_rejects_a_schema_that_is_no_class_once(
    tmp_path: Path,
    targets: ModuleType,
    capsys: pytest.CaptureFixture[str],
    schema: str,
    message: str,
):
    (tmp_path / "a.yaml").write_text("depth: 2\n")
    (tmp_path / "b.yaml").write_text("depth: 3\n")
    arguments = ["--schema", schema, str(tmp_path / "a.yaml"), str(tmp_path / "b.yaml")]
    assert _exit_code(["check", *arguments]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert message in output.err


def test_needs_a_config_file():
    assert _exit_code(["check", "--overrides", "a=1"]) == 2


def test_include_root_limits_the_includes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    (tmp_path / "configs").mkdir()
    (tmp_path / "outside.yaml").write_text("a: 1\n")
    path = tmp_path / "configs/app.yaml"
    path.write_text("n: ~include ../outside.yaml\n")
    main(["check", str(path)])
    capsys.readouterr()
    root = str(tmp_path / "configs")
    assert _exit_code(["check", str(path), "--include-root", root]) == 1
    assert "outside the include root" in capsys.readouterr().err
    missing = str(tmp_path / "missing")
    assert _exit_code(["check", str(path), "--include-root", missing]) == 2


def test_names_the_includes_that_led_to_a_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    (tmp_path / "model.yaml").write_text("optimizer: ~include missing.yaml\n")
    path = tmp_path / "main.yaml"
    path.write_text("model: ~include model.yaml\n")
    assert _exit_code(["check", str(path)]) == 1
    lines = capsys.readouterr().err.splitlines()
    assert "`optimizer`" in lines[0]
    assert "main.yaml" in lines[1]
