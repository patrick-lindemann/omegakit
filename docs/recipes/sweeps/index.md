# A sweep over settings

A benchmark or an experiment runs the same config many times, once for each
combination of a few values. Build the combinations in Python and give each one to
`load_config` as overrides. Every run gets its own independent config.

```{literalinclude} main.py
:language: python
:caption: main.py
```

```text
1 5 runs/w1-p5
1 20 runs/w1-p20
4 5 runs/w4-p5
4 20 runs/w4-p20
```

Each run's `log_dir` is an interpolation. Interpolations resolve after the overrides
are merged, so the directory name follows the swept values. Every value the grid
does not touch comes from the files as usual.

omegakit runs nothing in parallel and keeps no record of the runs. For sweeps with
launchers, parallel jobs or a sweeper that picks the next values, see how omegakit
[compares with Hydra](../../comparison/index.md#hydra). See
[Overrides](../../configs/overrides/index.md) and
[Interpolation](../../configs/interpolation/index.md).
