# export-schema

`omegakit export-schema` writes the JSON Schema of a class, which your YAML editor
uses to complete keys and mark mistakes while you type. How to set up the editor is
on [Editor support](../../schemas/editor-support/index.md).

Give it the import path of the root schema, and a file to write:

```sh
omegakit export-schema project.Experiment -o experiment.schema.json
```

Without `-o`, it prints the schema. For a file that holds a single node, such as one
model, export the schema of that node's class instead, such as `project.MLP`.

## Keeping the file current

When a class changes, its committed schema goes stale. `--check` writes nothing,
and fails when the file no longer matches the class, so CI catches it. A current
file prints nothing:

```sh
omegakit export-schema project.Experiment -o experiment.schema.json --check
```

## Rules

- `export-schema` takes the import path of a root schema dataclass, or of a
  `Configurable` class whose schema describes a fragment file. The schema is what
  `generate_json_schema` returns ([Editor support](../../schemas/editor-support/index.md#rules)).
- `--check` needs `-o`. It exits with 1 if the file is missing or differs from the
  generated schema, compared as JSON.
