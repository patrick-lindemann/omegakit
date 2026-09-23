import pytest
from omegaconf import OmegaConf

from omegakit import load_config

# Contracts: §1 Pipeline order, §2 Precedence. Each case is an assembled config and
# the hand-written YAML it must equal.

CASES = {
    "import": (
        {
            "lib.yaml": "opt:\n  lr: 5\n  items: [1, 2]\n",
            "main.yaml": "a: ~import lib.yaml\nb: '~import lib.yaml#opt.items'\n",
        },
        "a:\n  opt:\n    lr: 5\n    items: [1, 2]\nb: [1, 2]\n",
    ),
    "base": (
        {
            "main.yaml": (
                "n:\n"
                "  $base:\n"
                "    - {a: 1, b: 1, c: 1}\n"
                "    - {b: 2, c: 2}\n"
                "  c: 3\n"
                "  child:\n"
                "    $base: {x: 1}\n"
                "    y: 2\n"
            ),
        },
        "n:\n  a: 1\n  b: 2\n  c: 3\n  child: {x: 1, y: 2}\n",
    ),
    "defaults": (
        {
            "main.yaml": (
                "records:\n"
                "  $defaults:\n"
                "    path: data/${.id}.h5\n"
                "    opts: {a: 1, b: 2}\n"
                "  sphere: {id: sphere}\n"
                "  cube: {id: cube, opts: {b: 3}}\n"
                "  count: 2\n"
            ),
        },
        "records:\n"
        "  sphere:\n"
        "    id: sphere\n"
        "    path: data/${.id}.h5\n"
        "    opts: {a: 1, b: 2}\n"
        "  cube:\n"
        "    id: cube\n"
        "    path: data/${.id}.h5\n"
        "    opts: {a: 1, b: 3}\n"
        "  count: 2\n",
    ),
    "combined": (
        {
            "defaults.yaml": "timeout: 10\nretries: 3\n",
            "workers.yaml": (
                "$defaults:\n"
                "  $base: ~import defaults.yaml\n"
                "  $class: app.Worker\n"
                "fast: {timeout: 1}\n"
                "slow: {}\n"
            ),
            "main.yaml": (
                "workers:\n  $base: ~import workers.yaml\n  slow: {retries: 9}\n"
            ),
        },
        "workers:\n"
        "  fast: {timeout: 1, retries: 3, $class: app.Worker}\n"
        "  slow: {timeout: 10, retries: 9, $class: app.Worker}\n",
    ),
}


@pytest.mark.parametrize(("files", "expected"), CASES.values(), ids=CASES.keys())
def test_assembled_config_equals_hand_written(write_yaml, files, expected):
    paths = [write_yaml(name, text) for name, text in files.items()]
    written = OmegaConf.create(expected)
    assembled = load_config(paths[-1])
    assert OmegaConf.to_container(assembled) == OmegaConf.to_container(written)
    assert OmegaConf.to_container(assembled, resolve=True) == OmegaConf.to_container(
        written, resolve=True
    )
