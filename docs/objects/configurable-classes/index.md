# Configurable classes

A class can carry its own schema: subclass `Configurable[TConfig]` with a dataclass
`TConfig`. Use it when the config differs from the constructor, for example when a
factory picks the class to build. `curvefit`'s trainer takes the name of a learning
rate schedule, and returns the trainer for it:

```{literalinclude} ../../curvefit/curvefit/trainer.py
:language: python
:caption: curvefit/trainer.py (excerpt)
:start-at: "@dataclass"
:end-before: "    @abstractmethod"
```

```{literalinclude} main.py
:language: python
:caption: main.py
```

```text
CosineTrainer 50
ConstantTrainer 10
```

The config is checked against `TrainerConfig` before anything is built, so
`epochs: "50"` became the integer 50, and a schedule other than `constant` or
`cosine` is rejected ([Validation](../../schemas/validation/index.md)).
`from_config` then receives a `TrainerConfig`, with the right types for your editor,
and parses nothing. The fields and how they are checked are as for any
[dataclass schema](../../schemas/dataclass-schemas/index.md).

## `from_config`

`from_config` receives the typed config, with object fields already built, and
calls the constructor. The default passes every field. Override it when the config
and the constructor differ. A `from_config` that returns a subclass, as the
trainer's does, annotates the base class as its return type, since `Self` would
claim the class it was called on.

Keep `**kwargs` in the signature: arguments given to a partial from `prepare`
arrive there. Any class with a `from_config` classmethod works the same
([Instantiation](../instantiation/index.md#rules)).

A `TypedDict` `TConfig` gives `from_config` static types only: it receives a plain
`dict`, and the field values are not checked, though `$class` nodes inside are.

## Children that code chooses

`make_node` creates the node for a class, so code that picks a class itself, such
as a test or a `from_config`, gets the same checks and factory as a config does.
Above, `make_node(Trainer, epochs=10)` gave `{"$class": "curvefit.trainer.Trainer",
"epochs": 10}`, and the default schedule chose a `ConstantTrainer`.

## Checking the schema against the constructor

`check_schema(cls)` checks that a schema fits the constructor: every required
parameter has a field, and every field is a parameter of a matching type. It runs
by itself whenever the class is validated or built; call it in a test to catch a
mismatch without a config. It applies to the default `from_config` only, so the
trainer, whose factory calls the constructors itself, is not checked.

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
