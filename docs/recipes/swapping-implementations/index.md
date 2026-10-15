# Swapping implementations

An experiment often compares implementations: another model, another optimizer.
Type the field with a base class, name the implementation with `$target`, and swap
the whole node. The example project's `Experiment` dataclass types the model as
`nn.Module` and the optimizer as a callable that returns a `torch.optim.Optimizer`,
and its `DataConfig` types each dataset as a `Dataset`, so any subclass is
accepted. Its linear baseline names a linear model and SGD:

```{literalinclude} ../../example/configs/experiments/linear.yaml
:language: yaml
:caption: configs/experiments/linear.yaml
```

Assigning a node in code replaces it:

```{literalinclude} main.py
:language: python
:caption: main.py
```

```{code-block} text
:caption: Output

model: MLP
optimizer: Adam
error: Expected `Dataset`, but the config gives `$target: project.MLP`. (at `data.test`)
error: Adam.__init__() got an unexpected keyword argument 'momentum'
```

The linear baseline now trains an MLP with Adam, with Adam's settings only. A class
that is not a `Dataset` is rejected before anything is built.

An override, like a file, merges into the node it names
([Overrides](../../guide/overrides/index.md#rules)). Changing `$target` alone kept
SGD's `momentum`, which Adam does not take. Adam has no schema, so the mistake shows
only when the partial is called. Override `$target` alone only when the new class
takes the same settings. For a lasting swap, write an experiment file that names
the whole node, as `mlp.yaml` does: `base.yaml` names no optimizer, so there is
nothing to merge into. See [Instantiation](../../objects/instantiation/index.md)
and [TypedDict schemas](../../schemas/typed-dict-schemas/index.md).
