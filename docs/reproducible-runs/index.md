# Reproducible runs

A run is reproducible when the same experiment file, overrides and seed give the
same result. omegakit makes the config one file you can save and load again. The
rest is up to your entrypoint. This page shows how the example project's `main.py`
does it, and what omegakit leaves to you.

```{literalinclude} ../example/main.py
:language: python
:caption: main.py (excerpt)
:start-at: experiment_file, *overrides
:end-at: overrides.txt
```

## Seed before building

Constructors often draw random numbers: a PyTorch module draws its initial
weights. So `main.py` seeds PyTorch before it calls `instantiate`. Reading
`config.seed` resolves that one value; nothing is built yet. Seed every generator
your code uses, such as Python's `random`, NumPy's and PyTorch's. The `DataLoader`
shuffles with PyTorch's generator, so the same seed also gives the same batches.

## One directory per run

`base.yaml` derives the run directory from the config:

```{literalinclude} ../example/configs/base.yaml
:language: yaml
:caption: configs/base.yaml (excerpt)
:lines: 2-4
```

Interpolations resolve after the overrides are merged, so `seed=3` gives
`runs/mlp/seed3`, and each run of a [sweep](../recipes/parameter-sweeps/index.md)
gets its own directory. `run_dir.mkdir(parents=True)` fails when the directory
exists, so a run never overwrites another.

## Save the config and the overrides

`main.py` saves the config it built from, and the overrides it was given. The
saved config is assembled: the imports, bases and defaults are merged in, and the
overrides are applied. It is not resolved: `${seed}` stays as written, and so does
every other interpolation. Load it again to repeat the run:

```text
$ python main.py configs/experiments/mlp.yaml model.hidden=64
mlp: test loss 0.012
$ python main.py runs/mlp/seed0/config.yaml run_dir=runs/repeat
mlp: test loss 0.012
```

The saved config names its own run directory, so the repeat passes a new one. The
two runs also save the same weights to `model.pt`.

A secret read with `${secret:NAME}` stays in the saved file as written, so the run
directory holds no token ([Secrets](../security/secrets/index.md)).

## Check before running

Check every experiment file in CI, and look at a run before you launch it, with
[`omegakit check` and `omegakit show --resolve`](../command-line/index.md).

## Name runs by their config

To name or compare runs by what they ran, hash the resolved config in your own
code:

```{literalinclude} main.py
:language: python
:caption: main.py
```

```text
62234fd68935
```

## What omegakit does not do

- It creates no directories and writes no files. `main.py` does.
- It adds no timestamps. Add one to the run directory with your own resolver if you
  need it.
- It does not record the git commit or the package versions. Save them next to the
  config.
- It does not set determinism flags in your libraries, such as
  `torch.use_deterministic_algorithms`.
- It runs nothing in parallel and launches no jobs.

## Rules

- `load_config`, `validate`, `instantiate` and `prepare` write no files, create no
  directories and seed no random generator. Building calls your classes, which
  may.
- Assembly is deterministic: the same files, overrides, environment variables and
  resolvers give the same config.
- `OmegaConf.save` of a config from `load_config` writes it assembled and
  unresolved. `load_config` of that file gives an equal config, with one exception:
  a value that starts with `~import`, which an override can set, is an import when
  the saved file is loaded.
