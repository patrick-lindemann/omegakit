# show

`omegakit show` prints a config as `load_config` assembles it: after its imports,
bases, defaults and overrides. Use it to see what a file adds up to, and what values
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

name: linear
model:
  $class: torch.nn.Linear
  in_features: 1
  out_features: 1
optimizer:
  $class: torch.optim.SGD
  $partial: true
  lr: 0.1
  momentum: 0.9
seed: 0
run_dir: runs/${name}/seed${seed}
data:
  train:
    $class: project.SineWave
    'n': 256
    noise: 0.1
    seed: ${seed}
  test:
    $class: project.SineWave
    'n': 256
    noise: 0.1
    seed: 1234
loss:
  $ref: torch.nn.functional.mse_loss
epochs: 100
batch_size: 32
```

## One node

`--node` prints one node, by the same dotted path as `~import file#node`:

```sh
omegakit show configs/experiments/linear.yaml --node model
```

```{code-block} text
:caption: Output

$class: torch.nn.Linear
in_features: 1
out_features: 1
```

## Resolved values

`--resolve` resolves the interpolations, so you see the values a run gets. Here
the override of the seed reached the training split through `${seed}`:

```sh
omegakit show configs/experiments/mlp.yaml seed=3 --node data.train --resolve
```

```{code-block} text
:caption: Output

$class: project.SineWave
'n': 256
noise: 0.1
seed: 3
```

The values of `${secret:...}` print as `***`
([Secrets](../../security/secrets/index.md)). `--keep-meta` keeps the `$meta` keys
that `load_config` removes ([Metadata](../../guide/metadata/index.md)).

## Rules

- `show` takes one config file. It prints the assembled config, or the node at
  `--node`, as YAML. A scalar prints as its value.
- `--node` takes a dotted path, walked as `~import file#node` is: `items.0.name`,
  `items.-1`. A node that does not exist, or a path through an interpolation
  without `--resolve`, exits with 1.
- Without `--resolve`, values print as written: `${…}`, `???`, `null`. With it,
  interpolations on the path are followed and only the selected node is resolved.
  Missing values print as `???`, and any other resolution error exits with 1 with
  one line.
- With `--resolve`, every value that `${secret:...}` gives is printed as `***`,
  also inside longer strings and also when it is read outside `--node`.
  `--show-secrets` turns this off ([Secrets](../../security/secrets/index.md#rules)).
