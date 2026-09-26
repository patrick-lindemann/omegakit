# API reference

## Loading

```{eval-rst}
.. autofunction:: omegakit.load_config
```

## Instantiation

```{eval-rst}
.. autofunction:: omegakit.instantiate
.. autofunction:: omegakit.prepare
.. autoclass:: omegakit.Configurable
   :members: from_config
.. autofunction:: omegakit.make_node
```

## Typed configs

```{eval-rst}
.. autofunction:: omegakit.check_schema
.. autoexception:: omegakit.ConfigValidationError
```

## Validation

```{eval-rst}
.. autofunction:: omegakit.validate
.. autofunction:: omegakit.is_valid
```

## Editor schemas

```{eval-rst}
.. autofunction:: omegakit.generate_json_schema
```

## Traversal

```{eval-rst}
.. autofunction:: omegakit.walk
```

## Special keys

```{eval-rst}
.. automodule:: omegakit.keys
   :members:
```

## Resolvers

```{eval-rst}
.. automodule:: omegakit.resolvers.paths
   :members:
.. automodule:: omegakit.resolvers.torch
   :members:
```
