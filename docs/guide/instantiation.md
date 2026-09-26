# Instantiation

`instantiate(node)` builds Python objects from a config node. `$class` calls a class
or function, `$ref` imports an object without calling it, and `$partial` defers a
call.

## Example

```{literalinclude} ../examples/instantiation/shop.py
:language: python
:caption: shop.py
```

```{literalinclude} ../examples/instantiation/cart.yaml
:language: yaml
:caption: cart.yaml
```

```{literalinclude} ../examples/instantiation/main.py
:language: python
:caption: main.py
```

## `$class`

- The value is an import path, `module.attribute`. The attribute is imported and
  called with the node's other keys as keyword arguments.
- Nested `$class` nodes, in mappings and lists, are built first, and the parent
  receives the built objects.
- If the imported object has a `from_config` method, it is called with the arguments
  as one mapping instead ([Configurable](configurable.md)).
- The top-level node passed to `instantiate` must have `$class`.

## `$ref`

A `$ref` node is replaced by the imported object, uncalled: a function, a class or a
constant. It allows no other keys except `$meta`.

## `$partial` and `prepare`

- `$partial: true` turns a node into a `functools.partial` with its config arguments.
  Only `true` and `false` are accepted.
- `prepare(node)` does the same for the top-level node. Nested nodes are still built
  during `prepare`.
- Arguments passed when calling the partial win over config arguments of the same
  name. With `from_config`, they arrive as its `**kwargs`.

## Typing

The optional second argument, `instantiate(node, Cart)`, types the result as `Cart`
for pyright and editors. It is not checked at runtime. Without it the result is
`Any`.

## Errors

| Problem | Exception |
|---|---|
| Top-level node without `$class` | `ValueError` |
| Module not found | `ModuleNotFoundError` |
| Attribute not found | `ImportError` (`Could not import`) |
| `$ref` with other keys | `ValueError` |
| An unknown `$` key, or `$class` with `$ref` | `ValueError` (`reserved`) |
| `$partial` that is not a boolean | `ValueError` |
| A `???` in the node | `MissingMandatoryValue` |

An exception raised by a constructor or `from_config` keeps its type and message, and
gets a note such as `while instantiating items.0 (shop.Item)`. Errors raised later by
a partial get no note, because the call happens outside omegakit.
