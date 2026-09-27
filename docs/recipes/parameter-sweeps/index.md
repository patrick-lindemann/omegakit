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
poly3-sgd/seed0 0.0158
poly3-sgd/seed1 0.0156
poly3-adam/seed0 0.0377
poly3-adam/seed1 0.0233
poly5-sgd/seed0 0.0250
poly5-sgd/seed1 0.0244
poly5-adam/seed0 0.0305
poly5-adam/seed1 0.0275
```

The run directory is an interpolation of the name and the seed, which resolves
after the overrides are merged, so each run writes to its own directory
([Reproducible runs](../../reproducible-runs/index.md)). Here the override moves
all runs into a temporary directory.

The optimizer is a class, not a value, so the sweep builds its node with
`make_node` and assigns it, which replaces the whole node
([Swapping implementations](../swapping-implementations/index.md)). Each run seeds
the generator before it builds the model.

omegakit runs nothing in parallel and keeps no record of the runs. For launchers,
parallel jobs or a sweeper that picks the next values, see how omegakit
[compares with Hydra](../../comparison/index.md#hydra).
