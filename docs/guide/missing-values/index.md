# Missing values

`???` marks a value that someone else must fill, such as the name of an
experiment in a file that every experiment extends:

```{literalinclude} experiment.yaml
:language: yaml
:caption: experiment.yaml
```

```{literalinclude} main.py
:language: python
:caption: main.py
```

```{code-block} text
:caption: Output

missing keys: {'name'}
error: Missing mandatory value: name
missing keys: set()
config.name: wide
```

Once the name is set, here in code, the config is complete. A file that uses this
one as its `$base`, or an override, fills it the same way. To validate a file that
is incomplete on purpose, see
[Validation](../../schemas/validation/index.md#files-that-are-incomplete-on-purpose).

## Rules

- `???` stays through loading. A node that uses its file as `$base`, or an
  override, can fill it. A `???` of the node itself does not replace a value of its
  `$base`: the base's value stays.
- Reading a value that is still `???` raises OmegaConf's `MissingMandatoryValue`.
- `validate`, `instantiate` and `prepare` raise `ValidationMissingValueError`, a
  `ConfigValidationError`, without a `__cause__`: ``The value is `???`. Set it in
  the config or with an override. (at `name`)``. For a config that is `???` itself,
  the message is ``The config is `???`.``
- An `~include` of a node that holds `???` raises `ConfigIncludeError`
  ([Includes](../includes/index.md#rules)).
- `allow_missing=True` in `validate` and `is_valid`, and `--allow-missing` in
  `omegakit check`, accept `???`, required keys that are not given, and
  interpolations to missing or unknown keys. Every other value is still checked,
  except a plain list, tuple or mapping that holds a missing item, such as
  `betas: [0.9, ???]`. A special key, such as `$target`, still needs its value.
  `instantiate` and `prepare` take no such argument.
- `omegakit show --allow-missing` prints a `???`, and an interpolation to a missing
  or unknown key, as `???` instead of exiting with 1
  ([show](../../command-line/show/index.md#rules)).
- A required key that is not given may also stay open in a `$partial` node and at
  the root of `prepare`, to be given when the partial is called
  ([Instantiation](../../objects/instantiation/index.md)).
