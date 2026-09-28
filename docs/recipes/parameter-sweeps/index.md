# Parameter sweeps

A sweep runs the same experiment many times, once for each combination of a few
values. Build the combinations in Python and give each one to `load_config` as
overrides. Every run gets its own config, its own run directory and its own saved
copy of the config.

```{literalinclude} main.py
:language: python
:caption: main.py
```

```text
mlp8-sgd/seed0 0.015
mlp8-sgd/seed1 0.019
mlp8-adam/seed0 0.013
mlp8-adam/seed1 0.012
mlp32-sgd/seed0 0.012
mlp32-sgd/seed1 0.012
mlp32-adam/seed0 0.011
mlp32-adam/seed1 0.012
```

The run directory is an interpolation of the name and the seed, which resolves
after the overrides are merged, so each run writes to its own directory
([Reproducible runs](../../reproducible-runs/index.md)). Here the override moves
all runs into a temporary directory.

The optimizer is a class, not a value, so the sweep builds its node with
`make_node` and assigns it, which replaces the whole node
([Swapping implementations](../swapping-implementations/index.md)). Each run seeds
PyTorch before it builds the model, and `train` is the example project's training
loop.

omegakit runs nothing in parallel and keeps no record of the runs. For launchers,
parallel jobs or a sweeper that picks the next values, see how omegakit
[compares with Hydra](../../comparison/index.md#hydra).
