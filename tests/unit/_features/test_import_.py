from pathlib import Path

import pytest
from omegaconf import OmegaConf
from omegaconf.errors import InterpolationResolutionError, MissingMandatoryValue

from omegakit._core.file import (
    ConfigFileNotFoundError,
    ConfigSyntaxError,
    load_yaml,
)
from omegakit._features.import_ import (
    ImportCycleError,
    ImportInterpolationError,
    ImportMissingValueError,
    ImportNodeNotFoundError,
    ImportSyntaxError,
    ImportTypeError,
    resolve_imports,
)


def _load(path: Path):
    config = load_yaml(path)
    return resolve_imports(config, path)


def test_imports_a_whole_file(tmp_path: Path):
    (tmp_path / "model.yaml").write_text("hidden: 32")
    path = tmp_path / "main.yaml"
    path.write_text("model: ~import model.yaml")
    assert _load(path) == {"model": {"hidden": 32}}


@pytest.mark.parametrize(
    ("statement", "expected"),
    [
        pytest.param("~import other.yaml#model", {"hidden": 32}, id="mapping"),
        pytest.param("~import other.yaml#model.hidden", 32, id="nested-value"),
        pytest.param("~import other.yaml#seeds[1]", 7, id="list-item"),
        pytest.param("~import other.yaml#empty", None, id="null"),
        pytest.param("~import  other.yaml # model.hidden ", 32, id="whitespace"),
        pytest.param(
            "~import other.yaml#",
            {"model": {"hidden": 32}, "seeds": [3, 7], "empty": None},
            id="trailing-hash",
        ),
    ],
)
def test_imports_a_selected_node(tmp_path: Path, statement: str, expected):
    (tmp_path / "other.yaml").write_text(
        "model: {hidden: 32}\nseeds: [3, 7]\nempty: null"
    )
    path = tmp_path / "main.yaml"
    path.write_text(f'value: "{statement}"')
    assert _load(path).value == expected


def test_imports_from_a_file_that_holds_a_list(tmp_path: Path):
    (tmp_path / "seeds.yaml").write_text("[3, 7]")
    path = tmp_path / "main.yaml"
    path.write_text('seeds: ~import seeds.yaml\nfirst: "~import seeds.yaml#[0]"')
    assert _load(path) == {"seeds": [3, 7], "first": 3}


def test_imports_different_nodes_of_one_file(tmp_path: Path):
    (tmp_path / "models.yaml").write_text("small: {hidden: 32}\nlarge: {hidden: 256}")
    path = tmp_path / "main.yaml"
    path.write_text(
        'student: "~import models.yaml#small"\nteacher: "~import models.yaml#large"'
    )
    assert _load(path) == {"student": {"hidden": 32}, "teacher": {"hidden": 256}}


def test_a_node_may_be_selected_by_an_interpolation(tmp_path: Path):
    (tmp_path / "models.yaml").write_text("small: {hidden: 32}\nlarge: {hidden: 256}")
    path = tmp_path / "main.yaml"
    path.write_text('size: large\nmodel: "~import models.yaml#${size}"')
    assert _load(path).model == {"hidden": 256}


def test_a_node_path_follows_interpolations(tmp_path: Path):
    (tmp_path / "models.yaml").write_text("small: {hidden: 32}\ndefault: ${small}")
    path = tmp_path / "main.yaml"
    path.write_text('hidden: "~import models.yaml#default.hidden"')
    assert _load(path).hidden == 32


def test_imports_into_a_list_item(tmp_path: Path):
    (tmp_path / "model.yaml").write_text("hidden: 32")
    path = tmp_path / "main.yaml"
    path.write_text("models: [~import model.yaml, 1]")
    assert _load(path) == {"models": [{"hidden": 32}, 1]}


def test_a_list_file_can_import(tmp_path: Path):
    (tmp_path / "model.yaml").write_text("hidden: 32")
    path = tmp_path / "main.yaml"
    path.write_text("[~import model.yaml]")
    assert _load(path) == [{"hidden": 32}]


def test_a_path_is_relative_to_the_importing_file(tmp_path: Path):
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs/optimizer.yaml").write_text("lr: 0.1")
    (tmp_path / "configs/model.yaml").write_text("optimizer: ~import optimizer.yaml")
    path = tmp_path / "main.yaml"
    path.write_text("model: ~import configs/model.yaml")
    assert _load(path) == {"model": {"optimizer": {"lr": 0.1}}}


def test_imports_an_absolute_path(tmp_path: Path):
    (tmp_path / "elsewhere").mkdir()
    model_path = tmp_path / "elsewhere/model.yaml"
    model_path.write_text("hidden: 32")
    path = tmp_path / "main.yaml"
    path.write_text(f"model: ~import {model_path}")
    assert _load(path) == {"model": {"hidden": 32}}


def test_a_path_may_interpolate_keys_of_the_importing_file(tmp_path: Path):
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs/model.yaml").write_text("hidden: 32")
    path = tmp_path / "main.yaml"
    path.write_text('dir: configs\nmodel: "~import ${dir}/model.yaml"')
    assert _load(path).model == {"hidden": 32}


@pytest.mark.parametrize(
    "text",
    [
        pytest.param(
            'first: ~import first.yaml\nsecond: "~import ${first.next}"', id="after"
        ),
        pytest.param(
            'second: "~import ${first.next}"\nfirst: ~import first.yaml', id="before"
        ),
    ],
)
def test_a_path_does_not_see_keys_of_another_import(tmp_path: Path, text: str):
    (tmp_path / "first.yaml").write_text("next: second.yaml")
    (tmp_path / "second.yaml").write_text("a: 1")
    path = tmp_path / "main.yaml"
    path.write_text(text)
    with pytest.raises(ImportInterpolationError):
        _load(path)


def test_a_selected_value_is_resolved_in_the_imported_file(tmp_path: Path):
    (tmp_path / "other.yaml").write_text("base: 0.1\nlr: ${base}")
    path = tmp_path / "main.yaml"
    path.write_text('base: 5\nlr: "~import other.yaml#lr"')
    assert _load(path).lr == 0.1


def test_a_selected_mapping_resolves_in_the_assembled_config(tmp_path: Path):
    (tmp_path / "other.yaml").write_text("base: 0.1\noptimizer: {lr: '${base}'}")
    path = tmp_path / "main.yaml"
    path.write_text('base: 5\noptimizer: "~import other.yaml#optimizer"')
    assert _load(path).optimizer.lr == 5


@pytest.mark.parametrize(
    ("statement", "key"),
    [
        pytest.param("~import other.yaml#text", "value", id="selected"),
        pytest.param("~import other.yaml", "value.text", id="whole-file"),
    ],
)
def test_an_escaped_interpolation_stays_text(tmp_path: Path, statement: str, key: str):
    (tmp_path / "other.yaml").write_text(r"text: '\${not_a_key}'")
    path = tmp_path / "main.yaml"
    path.write_text(f'value: "{statement}"')
    assert OmegaConf.select(_load(path), key) == "${not_a_key}"


def test_two_imports_of_a_file_are_independent(tmp_path: Path):
    (tmp_path / "model.yaml").write_text("hidden: 32")
    path = tmp_path / "main.yaml"
    path.write_text("a: ~import model.yaml\nb: ~import model.yaml")
    config = _load(path)
    config.a.hidden = 64
    assert config.b.hidden == 32


def test_a_file_imported_through_two_files_is_no_cycle(tmp_path: Path):
    (tmp_path / "shared.yaml").write_text("seed: 0")
    (tmp_path / "left.yaml").write_text("shared: ~import shared.yaml")
    (tmp_path / "right.yaml").write_text("shared: ~import shared.yaml")
    path = tmp_path / "main.yaml"
    path.write_text("l: ~import left.yaml\nr: ~import right.yaml")
    assert _load(path) == {"l": {"shared": {"seed": 0}}, "r": {"shared": {"seed": 0}}}


@pytest.mark.parametrize(
    "value",
    ["~imported", "~importmodel.yaml", " ~import model.yaml", "see ~import model.yaml"],
)
def test_other_text_is_not_an_import(tmp_path: Path, value: str):
    (tmp_path / "model.yaml").write_text("hidden: 32")
    path = tmp_path / "main.yaml"
    path.write_text(f'value: "{value}"')
    assert _load(path).value == value


def test_the_default_returns_a_copy(tmp_path: Path):
    (tmp_path / "model.yaml").write_text("hidden: 32")
    content = {"model": "~import model.yaml"}
    config = OmegaConf.create(content)
    resolved_config = resolve_imports(config, tmp_path / "main.yaml")
    assert resolved_config is not config
    assert resolved_config == {"model": {"hidden": 32}}
    assert config == content


def test_without_a_copy_the_config_itself_is_changed(tmp_path: Path):
    (tmp_path / "model.yaml").write_text("hidden: 32")
    config = OmegaConf.create({"model": "~import model.yaml"})
    resolved_config = resolve_imports(config, tmp_path / "main.yaml", copy=False)
    assert resolved_config is config
    assert config == {"model": {"hidden": 32}}


def test_a_failure_leaves_the_config_unchanged(tmp_path: Path):
    (tmp_path / "model.yaml").write_text("hidden: 32")
    content = {"model": "~import model.yaml", "data": "~import nope.yaml"}
    config = OmegaConf.create(content)
    with pytest.raises(ConfigFileNotFoundError):
        resolve_imports(config, tmp_path / "main.yaml")
    assert config == content


def test_rejects_a_missing_file(tmp_path: Path):
    path = tmp_path / "main.yaml"
    path.write_text("model: ~import nope.yaml")
    with pytest.raises(ConfigFileNotFoundError, match=r"nope\.yaml"):
        _load(path)


def test_rejects_a_directory(tmp_path: Path):
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs/model.yaml").write_text("hidden: 32")
    path = tmp_path / "main.yaml"
    path.write_text("model: ~import configs")
    with pytest.raises(ConfigFileNotFoundError):
        _load(path)


def test_rejects_an_imported_file_with_invalid_yaml(tmp_path: Path):
    (tmp_path / "model.yaml").write_text("hidden: [1")
    path = tmp_path / "main.yaml"
    path.write_text("model: ~import model.yaml")
    with pytest.raises(ConfigSyntaxError, match=r"model\.yaml"):
        _load(path)


@pytest.mark.parametrize(
    "statement",
    [
        pytest.param("~import", id="no-file"),
        pytest.param("~import #model", id="only-a-node"),
        pytest.param("~import other.yaml#a#b", id="two-hashes"),
        pytest.param("~import other\\0.yaml", id="nul-in-path"),
    ],
)
def test_rejects_a_malformed_statement(tmp_path: Path, statement: str):
    path = tmp_path / "main.yaml"
    path.write_text(f'value: "{statement}"')
    with pytest.raises(ImportSyntaxError):
        _load(path)


@pytest.mark.parametrize("node_path", ["nope", "model.nope", "seeds.first", "seeds[5]"])
def test_rejects_a_node_that_does_not_exist(tmp_path: Path, node_path: str):
    (tmp_path / "other.yaml").write_text("model: {hidden: 32}\nseeds: [3, 7]")
    path = tmp_path / "main.yaml"
    path.write_text(f'value: "~import other.yaml#{node_path}"')
    with pytest.raises(ImportNodeNotFoundError, match=r"other\.yaml"):
        _load(path)


def test_rejects_a_node_that_holds_a_missing_value(tmp_path: Path):
    (tmp_path / "other.yaml").write_text("data: ???")
    path = tmp_path / "main.yaml"
    path.write_text('data: "~import other.yaml#data"')
    with pytest.raises(ImportMissingValueError, match=r"other\.yaml"):
        _load(path)


def test_a_missing_value_in_an_imported_mapping_stays_missing(tmp_path: Path):
    (tmp_path / "other.yaml").write_text("data: ???")
    path = tmp_path / "main.yaml"
    path.write_text("other: ~import other.yaml")
    assert OmegaConf.is_missing(_load(path).other, "data")


@pytest.mark.parametrize(
    "text",
    [
        pytest.param('model: "~import ${nope}/model.yaml"', id="in-the-path"),
        pytest.param('model: "~import other.yaml#broken"', id="in-the-node"),
    ],
)
def test_rejects_an_interpolation_that_does_not_resolve(tmp_path: Path, text: str):
    (tmp_path / "other.yaml").write_text("broken: ${nope}")
    path = tmp_path / "main.yaml"
    path.write_text(text)
    with pytest.raises(ImportInterpolationError):
        _load(path)


def test_rejects_a_file_that_imports_itself(tmp_path: Path):
    path = tmp_path / "main.yaml"
    path.write_text('a: "~import main.yaml#b"\nb: 1')
    with pytest.raises(ImportCycleError, match=r"main\.yaml"):
        _load(path)


def test_rejects_a_cycle_between_files(tmp_path: Path):
    (tmp_path / "a.yaml").write_text("b: ~import b.yaml")
    (tmp_path / "b.yaml").write_text("a: ~import a.yaml")
    path = tmp_path / "main.yaml"
    path.write_text("a: ~import a.yaml")
    with pytest.raises(ImportCycleError, match=r"a\.yaml"):
        _load(path)


def test_finds_a_cycle_through_another_spelling_of_a_path(tmp_path: Path):
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs/model.yaml").write_text(
        "main: ~import ../configs/../main.yaml"
    )
    path = tmp_path / "main.yaml"
    path.write_text("model: ~import configs/model.yaml")
    with pytest.raises(ImportCycleError):
        _load(path)


def test_finds_a_cycle_for_a_relative_config_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    (tmp_path / "main.yaml").write_text('a: "~import main.yaml#b"\nb: 1')
    monkeypatch.chdir(tmp_path)
    config = load_yaml(Path("main.yaml"))
    with pytest.raises(ImportCycleError):
        resolve_imports(config, "main.yaml")


def test_rejects_an_import_in_a_tuple():
    config = OmegaConf.create({"items": ("~import model.yaml",)})
    with pytest.raises(ImportTypeError):
        resolve_imports(config, "main.yaml")


def test_an_error_names_every_import_that_led_to_it(tmp_path: Path):
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs/model.yaml").write_text("optimizer: ~import nope.yaml")
    path = tmp_path / "main.yaml"
    path.write_text("model: ~import configs/model.yaml")
    with pytest.raises(ConfigFileNotFoundError) as error_info:
        _load(path)
    report = "\n".join([str(error_info.value), *error_info.value.__notes__])
    for text in ["nope.yaml", "~import nope.yaml", "model.yaml", "main.yaml"]:
        assert text in report


@pytest.mark.parametrize(
    ("error", "parent"),
    [
        (ImportSyntaxError, ValueError),
        (ImportInterpolationError, InterpolationResolutionError),
        (ImportTypeError, TypeError),
        (ImportMissingValueError, MissingMandatoryValue),
    ],
)
def test_an_error_is_also_its_builtin_or_omegaconf_error(
    error: type[Exception], parent: type[Exception]
):
    assert issubclass(error, parent)
