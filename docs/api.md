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
.. py:data:: omegakit.BASE_KEY
   :value: "$base"

   A mapping, or a list of mappings, merged underneath the node.

.. py:data:: omegakit.CLASS_KEY
   :value: "$class"

   Import path of the class or function a node is built with.

.. py:data:: omegakit.DEFAULTS_KEY
   :value: "$defaults"

   A mapping merged underneath every dict-valued sibling.

.. py:data:: omegakit.IMPORT_KEY
   :value: "~import"

   Value prefix that replaces a node with another config file or one of its nodes.

.. py:data:: omegakit.META_KEY
   :value: "$meta"

   Metadata attached to a node.

.. py:data:: omegakit.PARTIAL_KEY
   :value: "$partial"

   Flag that builds a `functools.partial` instead of calling the class.

.. py:data:: omegakit.REF_KEY
   :value: "$ref"

   Import path of an object that replaces the node without being called.
```

## Resolvers

```{eval-rst}
.. automodule:: omegakit.resolvers.paths
   :members:
.. automodule:: omegakit.resolvers.torch
   :members:
```
