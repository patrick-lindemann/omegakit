# Configurable classes

A class can carry its own schema: subclass `Configurable` and set `schema` to a
dataclass. Use it for a class that cannot be a dataclass itself, such as a PyTorch
module, or whose config differs from its constructor:

```{literalinclude} models.py
:language: python
:caption: models.py
```

```{literalinclude} main.py
:language: python
:caption: main.py
```

```{code-block} text
:caption: Output

model: MLP(
  (0): Linear(in_features=1, out_features=64, bias=True)
  (1): ReLU()
  (2): Linear(in_features=64, out_features=1, bias=True)
)
error: `activation` must be one of 'relu', 'tanh', but the config gives `'gelu'`.
node: {'$class': 'models.MLP', 'hidden': 8}
instantiate(node): MLP(
  (0): Linear(in_features=1, out_features=8, bias=True)
  (1): Tanh()
  (2): Linear(in_features=8, out_features=1, bias=True)
)
```

The config was checked against `MLPConfig` before anything was built, so
`hidden: "64"` became the integer 64, and `gelu` was rejected. The fields and how
they are checked are as for any
[dataclass schema](../../schemas/dataclass-schemas/index.md).

## `from_config`

`MLP` uses the default `from_config`, which passes every field of the typed config
to the constructor. Override it when the config and the constructor differ, for
example when a field names the subclass to build. Annotate its `config` with the
schema class to have it typed, and keep `**kwargs` in the signature, where
arguments given to a partial arrive. A `from_config` that returns a subclass
annotates the base class as its return type, since `Self` would claim the class it
was called on.

## Children that code chooses

`make_node` creates the node for a class, so code that picks a class itself, such
as a test or a `from_config`, gets the same checks as a config does.

## Rules

A class that subclasses `Configurable` and sets `schema` to a dataclass has that
dataclass as its **schema**. Its config is checked against it
([Dataclass schemas](../../schemas/dataclass-schemas/index.md#rules)) and built into
an instance of it, the typed config, which `from_config` receives.

**Schema lookup.** `schema` is a class attribute, so a subclass inherits it, and
`schema = None` in a subclass removes it. A `Configurable` without a schema gets
its built arguments as a mapping, unchecked. A `schema` that is not a dataclass
raises `SchemaDefinitionError`.

**Building a typed node**, in order:

1. Look up the schema.
2. Check the fields, as in
   [Dataclass schemas](../../schemas/dataclass-schemas/index.md#rules).
3. Build the object and `Any` fields, children first, as in
   [Instantiation](../instantiation/index.md#rules). A plain mapping in a field
   annotated with a dataclass is a section, built the same way. A built object's
   type is not checked again.
4. Call `schema(**fields)`, so `__post_init__` runs.
5. Call `from_config(typed_config)`, or build a partial of it that passes
   call-time arguments as `**kwargs`.

The whole node is validated before anything configured is built, so an error never
leaves some children built. Errors name the node path and the schema class.

**`from_config`** receives the typed config, children built, plus `**kwargs` from a
partial or a caller. It returns `Self`, or is annotated with a base class when it
returns a subclass. Calling it with a raw mapping works but is outside the rules.

**`make_node(target, **kwargs)`** returns `{"$class": "<module>.<qualname>",
**kwargs}` for a module-level class or function, for children that code chooses
in `from_config`. Overrides cannot reach such children. A target defined inside a
function or a class raises `ValueError`, because it cannot be imported by its
path.
