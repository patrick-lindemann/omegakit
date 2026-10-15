# show

`omegakit show` prints a config as `load_config` assembles it: after its includes,
bases, `$each` and overrides. Use it to see what a file adds up to, and what values
a run will get before you launch it.

An experiment file names its base and adds a few keys. `show` prints everything the
base brought in, with interpolations still as written:

```{literalinclude} ../../example/configs/experiments/linear.yaml
:language: yaml
:caption: configs/experiments/linear.yaml
```

```sh
omegakit show configs/experiments/linear.yaml
```

```{code-block} text
:caption: Output

$target: project.Experiment
seed: 0
name: linear
run_dir: runs/${name}/seed${seed}
data:
  train:
    $target: project.SineWave
    'n': 256
    noise: 0.1
    seed: ${seed}
  test:
    $target: project.SineWave
    'n': 256
    noise: 0.1
    seed: 1234
loss:
  $symbol: torch.nn.functional.mse_loss
epochs: 100
batch_size: 32
model:
  $target: torch.nn.Linear
  in_features: 1
  out_features: 1
optimizer:
  $target: torch.optim.SGD
  $partial: true
  lr: 0.1
  momentum: 0.9
```

## One node

`--node` prints one node, selected as `~include file#node` selects it:

```sh
omegakit show configs/experiments/linear.yaml --node model
```

```{code-block} text
:caption: Output

$target: torch.nn.Linear
in_features: 1
out_features: 1
```

## Resolved values

`--resolve` resolves the interpolations, so you see the values a run gets. Here
the override of the seed reached the training split through `${seed}`:

```sh
omegakit show configs/experiments/mlp.yaml --overrides seed=3 --node data.train --resolve
```

```{code-block} text
:caption: Output

$target: project.SineWave
'n': 256
noise: 0.1
seed: 3
```

In a file that is incomplete on purpose, such as a base that every experiment
extends, an interpolation can lead to a `???`. `run_dir` needs the `name` that
only the experiments give:

```sh
omegakit show configs/base.yaml --node run_dir --resolve
```

```{code-block} text
:caption: Output

configs/base.yaml: InterpolationToMissingValueError: MissingMandatoryValue while resolving interpolation: Missing mandatory value: name
```

`--allow-missing` prints `???` for it instead of exiting with 1
([Missing values](../../guide/missing-values/index.md)):

```sh
omegakit show configs/base.yaml --node run_dir --resolve --allow-missing
```

```{code-block} text
:caption: Output

???
```

The values of `${secret:...}` print as `***`
([Secrets](../../security/secrets/index.md)). `--keep-meta` keeps the `$meta` keys
that `load_config` removes ([Metadata](../../guide/metadata/index.md)).

## Rules

- `omegakit show CONFIG [--overrides KEY=VALUE ...] [--node KEY] [--resolve]
  [--allow-missing] [--keep-meta] [--show-secrets] [--include-root DIR]`.
- `show` takes one config file. It prints the assembled config, or the node at
  `--node`, as YAML. A scalar prints as its value.
- `--keep-meta` and `--include-root` are passed to `load_config` as `keep_meta`
  and `include_root` ([Includes](../../guide/includes/index.md#rules)). An
  `--include-root` that is not a directory is a usage error, and the command exits
  with 2.
- A file that cannot be loaded or a node that cannot be resolved prints
  `<file>: <exception type>: <message>` to stderr, as `check` does, and the
  command exits with 1.
- `--overrides KEY=VALUE ...` applies in the order given, as the `overrides` of
  `load_config`, and takes its arguments as `check` does
  ([check](../check/index.md#rules)).
- `--node` selects a node with `OmegaConf.select`, as `~include file#node` does
  ([Includes](../../guide/includes/index.md#rules)): `items.0.name`,
  `items[0].name`, `items.-1`. A node that does not exist exits with 1, and so
  does a node that holds `???`, unless `--allow-missing` is given.
- Without `--resolve`, a mapping or a list prints as written: `${…}`, `???`,
  `null`. A single value that `--node` selects prints resolved, as
  `OmegaConf.select` gives it. With `--resolve`, the selected node is resolved and
  nothing else. A `???` prints as `???`, and an interpolation that cannot be
  resolved exits with 1.
- `--allow-missing` prints `???` for a node that holds `???` and for an
  interpolation to a missing or unknown key, instead of exiting with 1. Any other
  resolution error still exits with 1.
- `${secret:...}` resolves to `***`, unless `--show-secrets` is given
  ([Secrets](../../security/secrets/index.md#rules)).
