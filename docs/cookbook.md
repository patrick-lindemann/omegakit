# Cookbook

Complete patterns, each a runnable example.

## Reusable library configs

A library file defines a service with `???` slots. Each consumer imports it as a
`$base` and fills the slots; `is_valid` reports a slot that is still open.

```{literalinclude} examples/cookbook-library-slots/library/service.yaml
:language: yaml
:caption: library/service.yaml
```

```{literalinclude} examples/cookbook-library-slots/app.yaml
:language: yaml
:caption: app.yaml
```

```{literalinclude} examples/cookbook-library-slots/main.py
:language: python
:caption: main.py
```

## Experiment sweeps

One base config and a grid of dotlist overrides give one independent config per run.
The run name is an interpolation, so it follows the overridden values.

```{literalinclude} examples/cookbook-sweeps/experiment.yaml
:language: yaml
:caption: experiment.yaml
```

```{literalinclude} examples/cookbook-sweeps/main.py
:language: python
:caption: main.py
```

## Dataset manifests

`$defaults` with `$class` makes every entry of a manifest a `Dataset`, with shared
settings. An entry can extend another one with `$base`.

```{literalinclude} examples/cookbook-manifests/data.py
:language: python
:caption: data.py
```

```{literalinclude} examples/cookbook-manifests/manifest.yaml
:language: yaml
:caption: manifest.yaml
```

```{literalinclude} examples/cookbook-manifests/main.py
:language: python
:caption: main.py
```

## A typed model with a configurable encoder

The model's schema types `encoder` as the `Encoder` base class. Each encoder has its
own schema, a nested interpolation picks one, and a single override switches it.
`validate` checks everything before a model is built.

```{literalinclude} examples/cookbook-typed-model/model.py
:language: python
:caption: model.py
```

```{literalinclude} examples/cookbook-typed-model/app.yaml
:language: yaml
:caption: app.yaml
```

```{literalinclude} examples/cookbook-typed-model/main.py
:language: python
:caption: main.py
```
