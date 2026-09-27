# Reproducible runs

A run is reproducible when the same experiment file, overrides and seed give the
same result. omegakit makes the config one file you can save and load again. The
rest is up to your entrypoint. This page shows how `curvefit`'s `main.py` does it,
and what omegakit leaves to you.

```{literalinclude} ../curvefit/main.py
:language: python
:caption: main.py (excerpt)
:start-at: experiment_file, *overrides
:end-at: overrides.txt
```

## Seed before building

Constructors often draw random numbers: `curvefit`'s models draw their initial
coefficients. So `main.py` seeds the generator before it calls `instantiate`.
Reading `config.seed` resolves that one value; nothing is built yet. Seed every
generator your code uses, such as Python's `random`, NumPy's and PyTorch's.

## One directory per run

`base.yaml` derives the run directory from the config:

```{literalinclude} ../curvefit/configs/base.yaml
:language: yaml
:caption: configs/base.yaml (excerpt)
:lines: 2-4
```

Interpolations resolve after the overrides are merged, so `seed=3` gives
`runs/poly3-adam/seed3`, and each run of a [sweep](../recipes/parameter-sweeps/index.md)
gets its own directory. `run_dir.mkdir(parents=True)` fails when the directory
exists, so a run never overwrites another.

## Save the config and the overrides

`main.py` saves the config it built from, and the overrides it was given. The
saved config is assembled: the imports, bases and defaults are merged in, and the
overrides are applied. It is not resolved: `${seed}` and `${oc.env:...}` stay as
written, so the file holds no secret values. Load it again to repeat the run:

```text
$ python main.py configs/experiments/poly3-adam.yaml model.degree=5
poly3-adam: train loss 0.0300
test mse: 0.0305
test mae: 0.1427
$ python main.py runs/poly3-adam/seed0/config.yaml run_dir=runs/repeat
poly3-adam: train loss 0.0300
test mse: 0.0305
test mae: 0.1427
```

The saved config names its own run directory, so the repeat passes a new one.

To show a run to people, you can also save a resolved copy with its secrets masked,
`OmegaConf.save(mask_secrets(config), run_dir / "config.masked.yaml")`. Do not
repeat a run from it: masked values load back as `***`
([Masking secrets](../security/masking-secrets/index.md)).

## Check before running

Check every experiment file in CI, and look at a run before you launch it, with
[`omegakit check` and `omegakit show --resolve`](../tools/command-line/index.md).

## Name runs by their config

To name or compare runs by what they ran, hash the resolved config in your own
code:

```{literalinclude} main.py
:language: python
:caption: main.py
```

```text
99d45fba49c0
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
