# Swapping implementations

An experiment often compares implementations: another optimizer, another dataset.
Type the field with a base class, name the implementation with `$class`, and swap
the whole node. `curvefit`'s datasets share a base class:

```{literalinclude} ../../curvefit/curvefit/data.py
:language: python
:caption: curvefit/data.py (excerpt)
:start-at: "class Dataset"
```

`Experiment` types each split as a `Dataset`, the model as a `Model` and the
optimizer as a callable that returns an `Optimizer`, so any subclass is accepted.
Assigning a node in code replaces it:

```{literalinclude} main.py
:language: python
:caption: main.py
```

```text
CsvData Adam
`data.test` expects Dataset, but the config gives `$class: curvefit.models.Polynomial`.
Adam.__init__() got an unexpected keyword argument 'momentum'
```

The test split now reads the measurements, and the optimizer is Adam with its own
settings only. A class that is not a `Dataset` is rejected before anything is
built.

An override, like a file, merges into the node it names
([Overrides](../../configs/overrides/index.md#rules)). Changing `$class` alone kept
SGD's `momentum`, which Adam does not take. Adam has no schema, so the mistake shows
only when the partial is called. Override `$class` alone only when the new class
takes the same settings. For a lasting swap, write an experiment file that names
the whole node, as `poly3-adam.yaml` does: `base.yaml` names no optimizer, so there
is nothing to merge into. See [Instantiation](../../objects/instantiation/index.md)
and [Dataclass schemas](../../schemas/dataclass-schemas/index.md).
