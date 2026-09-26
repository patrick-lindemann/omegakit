# Metadata

`$meta` holds notes that are not configuration: authors, descriptions, review dates.
It can appear in any mapping.

## Example

```{literalinclude} ../examples/metadata/app.yaml
:language: yaml
:caption: app.yaml
```

```{literalinclude} ../examples/metadata/main.py
:language: python
:caption: main.py
```

## Rules

- `load_config` strips `$meta` everywhere, unless `keep_meta=True`.
- `instantiate` never passes `$meta` to a constructor or to `from_config`, even when
  it was kept.
- `$meta` is the only `$` key allowed next to `$ref` and in plain mappings that are
  instantiated.
