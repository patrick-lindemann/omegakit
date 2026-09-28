# Configurable classes

A class can carry its own schema: subclass `Configurable[TConfig]` with a dataclass
`TConfig`. Use it for a class that cannot be a dataclass itself, such as a PyTorch
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
example when a field names the subclass to build. Keep `**kwargs` in the signature,
where arguments given to a partial arrive. A `from_config` that returns a subclass
annotates the base class as its return type, since `Self` would claim the class it
was called on.

## Children that code chooses

`make_node` creates the node for a class, so code that picks a class itself, such
as a test or a `from_config`, gets the same checks as a config does.

## Checking the schema against the constructor

`check_schema(cls)` checks that a schema fits the constructor. It runs by itself
whenever the class is validated or built; call it in a test to catch a mismatch
without a config, as `main.py` does for `MLP`.

## Rules

A class that subclasses `Configurable[TConfig]` with a dataclass `TConfig` has
`TConfig` as its **schema**. Its config is checked against it
([Dataclass schemas](../../schemas/dataclass-schemas/index.md#rules)) and built into
a `TConfig` instance, the typed config, which `from_config` receives.

**Schema lookup.** The `TConfig` argument is found by walking the original bases
of the `$class` and substituting type variables, so `class Sub(Mixin[int], Model)`
and `class Leaf(Mid[Config])` work. An unparametrized generic class uses its type
variable's default, or has no schema. A type variable that cannot be substituted
raises `SchemaDefinitionError`. The result is cached per class.

**Building a typed node**, in order:

1. Look up the schema.
2. Run `check_schema`, unless a class in the MRO below `Configurable` overrides
   `from_config`.
3. Check the fields, as in
   [Dataclass schemas](../../schemas/dataclass-schemas/index.md#rules).
4. Build the object and `Any` fields, children first, as in
   [Instantiation](../instantiation/index.md#rules). A plain mapping in a field
   annotated with a dataclass is a section, built the same way. A built object's
   type is not checked again.
5. Call `TConfig(**fields)`, so `__post_init__` runs.
6. Call `from_config(typed_config)`, or build a partial of it that passes
   call-time arguments as `**kwargs`.

The whole node is validated before anything configured is built, so an error never
leaves some children built. Errors name the node path and the schema class.

**`check_schema(cls)`** checks that the schema fits `__init__`, and is cached once
it passes. Every required `__init__` parameter needs a field. Every field must be a
keyword parameter, unless `__init__` takes `**kwargs`; a positional-only parameter
is rejected even then. Every field's annotation must be assignable to its
parameter's: `int` to `float`, a subclass to its base, unions member by member.
Generic annotations are skipped, and so is each parameter whose annotation does not
resolve. A mismatch raises `SchemaDefinitionError` naming the field or parameter. It
passes unchecked a class without a schema, a dataclass that is its own schema, and a
class whose MRO overrides `from_config`.

**`from_config`** receives the typed config, children built, plus `**kwargs` from a
partial or a caller. It returns `Self`, or is annotated with a base class when it
returns a subclass. Calling it with a raw mapping works but is outside the rules.

**`make_node(target, **kwargs)`** returns `{"$class": "<module>.<qualname>",
**kwargs}` for a module-level class or function, for children that code chooses
in `from_config`. Overrides cannot reach such children. A target defined inside a
function or a class raises `ValueError`, because it cannot be imported by its
path.
