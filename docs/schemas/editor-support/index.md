# Editor support

The dataclasses that validate a config can also describe it to your YAML editor, as
a JSON Schema: the editor then completes keys and marks mistakes while you type.
From the example project's directory:

```text
$ omegakit json-schema project.Experiment -o experiment.schema.json
```

The first line of each experiment file names the schema, which is how the YAML
extension for VS Code by Red Hat, and other editors that use yaml-language-server,
find it:

```{literalinclude} ../../example/configs/experiments/mlp.yaml
:language: yaml
:caption: configs/experiments/mlp.yaml
:lines: 1-3
```

The import path must be importable from the current directory, as for `$class`.
`generate_json_schema(Experiment)` returns the same schema as a dictionary. For a
file that holds a single node, such as one model, generate the schema of that
node's class instead, such as `project.MLP`.

Run the same command with `--check` in CI. It writes nothing, and exits with 1 when
the committed file no longer matches the classes:

```text
$ omegakit json-schema project.Experiment -o experiment.schema.json --check
```

## What the editor checks

Misspelled keys and values of the wrong type are errors at the root, in sections
such as `data`, and inside a node whose `$class` names exactly the class the field
expects, when that class has a schema. The editor knows nothing about subclasses,
so under `model: nn.Module` a `$class: project.MLP` node is accepted as any mapping;
`validate` still checks it.

What the schema cannot know is allowed everywhere: interpolations, `???`, `~import`
and keys that start with `$`. Nothing is required, because a value may still come
from a `$base`, `$defaults`, an import or an override; `validate` reports what is
missing. Enums accept their member names and values, and `Literal` fields their
values.

In VS Code with the Red Hat YAML extension, errors appear for wrong types and
misspelled keys, completion offers the root's keys, `Literal` values and the fields
of a `$class` node, and hover shows a field's type.

## Rules

`generate_json_schema(schema)` and `omegakit json-schema` produce a draft-07 JSON
Schema for YAML files, from a root schema dataclass or from a `Configurable` class
whose schema describes a fragment file. Anything else raises `TypeError`.

- Any value, scalar or node, may also be `${…}`, `???` or an `~import`.
- Any mapping accepts `$` keys. Other unknown keys are errors.
- Nothing is required: values may come from `$base`, `$defaults`, imports or
  overrides. `validate` reports what is missing.
- Enums list their member names, and the `str` and `int` values that are not also
  a name. `Literal` fields list their values. Fixed-length tuples have one schema
  per position.
- An object field of a `Configurable` class with a dataclass schema is checked
  against that schema only when its `$class` is the class's defining module and
  qualified name. Any other `$class`, such as a re-export or a subclass, accepts
  any mapping.
- No field descriptions are generated.
