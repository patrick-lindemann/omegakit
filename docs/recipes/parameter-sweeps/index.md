# Parameter sweeps

A sweep runs the same experiment many times, once for each combination of a few
values. Build the combinations in Python and give each one to `load_config` as
overrides. Every run gets its own config, its own run directory and its own saved
copy of the config. This sweep starts from an experiment file of the example
project:

```{literalinclude} ../../example/configs/experiments/mlp.yaml
:language: yaml
:caption: configs/experiments/mlp.yaml
```

Its base, `configs/base.yaml`, sets the seed and derives `run_dir` from `name` and
`seed`. `train` is the project's plain PyTorch training loop, and returns the loss
on the test split:

```{literalinclude} main.py
:language: python
:caption: main.py
```

```{code-block} text
:caption: Output

mlp8-sgd/seed0: 0.015
mlp8-sgd/seed1: 0.019
mlp8-adam/seed0: 0.013
mlp8-adam/seed1: 0.012
mlp32-sgd/seed0: 0.012
mlp32-sgd/seed1: 0.012
mlp32-adam/seed0: 0.011
mlp32-adam/seed1: 0.012
```

The `run_dir` override moves the run directories into a temporary directory. The
optimizer is a class, not a value, so
the sweep builds its node with `make_node` and assigns it, which replaces the whole
node ([Swapping implementations](../swapping-implementations/index.md)).

For launchers, parallel jobs or a sweeper that picks the next values, see how
omegakit [compares with Hydra](../../comparison/index.md#hydra).
