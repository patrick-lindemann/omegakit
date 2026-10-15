# API

```{eval-rst}
.. py:data:: omegakit.__version__
   :type: str
```

## Loading

```{eval-rst}
.. autofunction:: omegakit.load_config
```

## Building

```{eval-rst}
.. autofunction:: omegakit.instantiate
.. autofunction:: omegakit.prepare
.. autoclass:: omegakit.Configurable
   :members: schema, from_config
.. autofunction:: omegakit.make_node
```

## Checking

```{eval-rst}
.. autofunction:: omegakit.validate
.. autofunction:: omegakit.is_valid
```

## Nodes

```{eval-rst}
.. autofunction:: omegakit.walk
.. py:data:: omegakit.Config
   :value: DictConfig | ListConfig | TupleConfig

   A config node that holds other nodes: a mapping, a list or a tuple.

.. autofunction:: omegakit.cast_config
```

## Special keys

```{eval-rst}
.. autodata:: omegakit.ARGS_KEY

.. autodata:: omegakit.BASE_KEY

.. autodata:: omegakit.EACH_KEY

.. autodata:: omegakit.INCLUDE_KEY

.. autodata:: omegakit.META_KEY

.. autodata:: omegakit.PARTIAL_KEY

.. autodata:: omegakit.SYMBOL_KEY

.. autodata:: omegakit.TARGET_KEY
```

## Errors

```{eval-rst}
.. autoexception:: omegakit.OmegaKitBaseException
.. autoexception:: omegakit.ConfigLoadError
.. autoexception:: omegakit.ConfigValidationError
.. autoexception:: omegakit.ConfigFileNotFoundError
.. autoexception:: omegakit.ConfigFilePermissionError
.. autoexception:: omegakit.ConfigFileSyntaxError
.. autoexception:: omegakit.QualifiedNameSyntaxError
.. autoexception:: omegakit.QualifiedNameNotFoundError
.. autoexception:: omegakit.ConfigMergeError
.. autoexception:: omegakit.ConfigIncludeError
.. autoexception:: omegakit.IncludeRootError
.. autoexception:: omegakit.ConfigOverrideError
.. autoexception:: omegakit.ValidationInterpolationError
.. autoexception:: omegakit.ValidationMissingValueError
.. autoexception:: omegakit.ConfigTargetError
.. autoexception:: omegakit.ConfigSymbolError
.. autoexception:: omegakit.ConfigSchemaError
.. autoexception:: omegakit.SchemaDefinitionError
```

## Resolvers

```{eval-rst}
.. automodule:: omegakit.resolvers.paths
   :members:
.. automodule:: omegakit.resolvers.secrets
   :members:
.. automodule:: omegakit.resolvers.torch
   :members:
.. automodule:: omegakit.resolvers.numpy
   :members:
```
