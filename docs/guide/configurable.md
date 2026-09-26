# Configurable

Any class can be built from a config: `$class` calls its constructor with the node's
arguments. Subclass `Configurable` when construction needs more than that, or
`Configurable[TConfig]` to validate the config against a dataclass schema
([Typed configs](typed-configs.md)).

## Example

```{literalinclude} ../examples/configurable/pipeline.py
:language: python
:caption: pipeline.py
```

```{literalinclude} ../examples/configurable/pipelines.yaml
:language: yaml
:caption: pipelines.yaml
```

```{literalinclude} ../examples/configurable/main.py
:language: python
:caption: main.py
```

## `from_config`

- When the class has `from_config`, `instantiate` calls `from_config(arguments)`
  instead of the constructor. `arguments` is a plain `dict` with nested objects
  already built, or the typed config when the class has a schema.
- The default `Configurable.from_config` calls `cls(**arguments, **kwargs)`.
- Override it to translate the config, such as building objects from names. Keep
  `**kwargs` in the signature: call-time arguments of a partial arrive there.
- `from_config` is duck-typed. `Configurable` is one implementation, and any class
  with a `from_config` classmethod behaves the same.
