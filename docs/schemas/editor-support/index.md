# Editor support

The dataclasses that validate a config can also describe it to your YAML editor, as
a JSON Schema: the editor then completes keys and marks mistakes while you type.
The schema of an experiment is a dataclass in `schemas.py`:

```{literalinclude} schemas.py
:language: python
:caption: schemas.py
```

`omegakit export-schema` writes its JSON Schema, run from the directory that
`schemas.py` is in:

```sh
omegakit export-schema schemas.Experiment -o experiment.schema.json
```

The first line of the config file names the schema, which is how the YAML extension
for VS Code by Red Hat, and other editors that use yaml-language-server, find it:

```{literalinclude} experiment.yaml
:language: yaml
:caption: experiment.yaml
```

`generate_json_schema(Experiment)` returns the same schema as a dictionary. For a
file that holds a single node, generate the schema of that node's class instead.

Run the same command with `--check` in CI, to fail when the committed file no
longer matches the classes:

```sh
omegakit export-schema schemas.Experiment -o experiment.schema.json --check
```

In VS Code with the Red Hat YAML extension, errors appear for wrong types and
misspelled keys, completion offers the root's keys, `Literal` values and the fields
of a `$class` node, and hover shows a field's type. What the schema checks is listed
under Rules; `validate` checks the rest.

## Rules

`generate_json_schema(schema)` and `omegakit export-schema` produce a draft-07 JSON
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
