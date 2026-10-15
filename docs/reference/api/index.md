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
.. py:data:: omegakit.ARGS_KEY
   :value: "$args"

   The key of the list of positional arguments of the `$target`.

.. py:data:: omegakit.BASE_KEY
   :value: "$base"

   The key of a mapping, or a list of mappings, merged under its node.

.. py:data:: omegakit.EACH_KEY
   :value: "$each"

   The key of a mapping merged under every mapping beside it.

.. py:data:: omegakit.INCLUDE_KEY
   :value: "~include"

   The prefix of a value that is replaced by a config file or one of its nodes.

.. py:data:: omegakit.META_KEY
   :value: "$meta"

   The key of data about a node, which `load_config` removes.

.. py:data:: omegakit.PARTIAL_KEY
   :value: "$partial"

   The key that, set to `true`, builds a partial of the `$target` instead.

.. py:data:: omegakit.SYMBOL_KEY
   :value: "$symbol"

   The key of the import path of an object that replaces its node as it is.

.. py:data:: omegakit.TARGET_KEY
   :value: "$target"

   The key of the import path of the class or function that builds its node.
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
