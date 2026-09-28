# Swapping implementations

An experiment often compares implementations: another model, another optimizer.
Type the field with a base class, name the implementation with `$class`, and swap
the whole node. The example project's `Experiment` types the model as `nn.Module`,
each split as a `Dataset`, and the optimizer as a callable that returns a
`torch.optim.Optimizer`:

```{literalinclude} ../../example/project.py
:language: python
:caption: project.py (excerpt)
:start-after: "    test: Dataset"
:end-at: "batch_size: int = 32"
:lines: 3-
```

So any subclass is accepted. Assigning a node in code replaces it:

```{literalinclude} main.py
:language: python
:caption: main.py
```

```text
MLP Adam
`data.test` expects Dataset, but the config gives `$class: project.MLP`.
Adam.__init__() got an unexpected keyword argument 'momentum'
```

The linear baseline now trains an MLP with Adam, with Adam's settings only. A class
that is not a `Dataset` is rejected before anything is built.

An override, like a file, merges into the node it names
([Overrides](../../guide/overrides/index.md#rules)). Changing `$class` alone kept
SGD's `momentum`, which Adam does not take. Adam has no schema, so the mistake shows
only when the partial is called. Override `$class` alone only when the new class
takes the same settings. For a lasting swap, write an experiment file that names
the whole node, as `mlp.yaml` does: `base.yaml` names no optimizer, so there is
nothing to merge into. See [Instantiation](../../objects/instantiation/index.md)
and [Dataclass schemas](../../schemas/dataclass-schemas/index.md).
