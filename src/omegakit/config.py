from __future__ import annotations

from pathlib import Path
from typing import Any, Generic

from omegaconf import DictConfig, ListConfig, OmegaConf
from typing_extensions import TypeVar

type PathLike = Path | str

TConfig = TypeVar("TConfig", default=DictConfig)


META_KEY = "$meta"
"""Arbitrary metadata attached to any node, e.g. `$meta: {author: myname}`.

Preserved on load only when `load_config(..., keep_meta=True)`, and always ignored by
`instantiate` (never passed to a constructor).
"""

IMPORT_KEY = "~import"
"""String value replacing a node with another config file, `~import <path>[#<node>]`.

A relative path is resolved against the importing file, an absolute path is used as-is;
the optional `#<node>` selects a subnode of the imported config (e.g. `~import
models/base.yaml#optimizer`). Circular imports raise a `ValueError`.

The statement may contain `${...}` interpolations (e.g. `~import
${paths:config_dir}/models/base.yaml`). Being part of the reference itself, they are
resolved eagerly at assembly time — per file, before any `$base` merge — so resolvers
are always available, but config-value references only see keys literally present in
the importing file at that point.
"""

BASE_KEY = "$base"
"""Defaults merged into the current node, e.g. `$base: {lr: 0.1, steps: 100}`.

The `$base` mapping is merged underneath the node (the node's own keys win) before
instantiation. Bases are merged bottom-up, so nested nodes resolve their own `$base`
first. Typically populated via `~import` or an interpolation (`$base: ${..._common}`).

Resolution contract: assembly (`~import` + `$base` merge) is structural and resolves
nothing except the `$base`/`~import` reference itself (it decides what to merge).
Every `${...}` interpolation and `???` mandatory-missing value is carried through
untouched and resolved once, later — lazily on access, or when `instantiate` builds the
object tree — against the fully-assembled config. So a `???` means "a `$base` consumer
must supply this key"; unfilled, it errors at use time (naming the key), never during
assembly.
"""

DEFAULTS_KEY = "$defaults"
"""Defaults merged underneath every dict-valued sibling of the containing mapping.

Scalar and list-valued siblings and `$`-keys are untouched. Item keys win, and passes
run bottom-up, so an inner `$defaults` wins over an outer one.

Follows the `$base` resolution contract: only the `$defaults` reference itself is
resolved eagerly; every `${...}` inside the values is carried through and resolved
lazily at the item's final position — relative interpolations (`${.id}`) are written
as-if already inside an item, absolute ones resolve from the config root.
"""

CLASS_KEY = "$class"
"""Import path of the class to build from a node, e.g. `$class: myapp.models.Foo`.

Its presence marks a node as instantiable: `instantiate` imports the class and calls it
(or its `from_config`) with the node's other keys as keyword arguments.
"""

REF_KEY = "$ref"
"""Import path resolved to the referenced object itself, e.g. `$ref: torch.float32`.

Unlike `$class` the object is imported but not called. A `$ref` node must contain no
other keys (`$meta` aside).
"""

PARTIAL_KEY = "$partial"
"""Flag deferring instantiation of a `$class` node, e.g. `$partial: true`.

When true, `instantiate` returns a `functools.partial` bound to the resolved arguments
instead of the constructed object, so remaining arguments can be supplied at call time.
"""


class Configurable(Generic[TConfig]):
    """A class that can be instantiated from a config."""

    @classmethod
    def from_config(
        cls, config: TConfig | DictConfig | dict[str, Any], **kwargs
    ) -> Any:
        """Create an instance from a materialized config.

        Args:
            config: The constructor arguments, keyed by parameter name.
            **kwargs: Extra arguments for subclasses. The default implementation
                ignores them.

        Returns:
            The created instance.
        """
        return cls(**config)


def load_config(
    file_path: PathLike,
    *,
    overrides: DictConfig | dict[str, Any] | list[str] | None = None,
    keep_targets: bool = True,
    keep_meta: bool = False,
) -> DictConfig:
    """Load a YAML configuration file from a given file path.

    Args:
        file_path: The path to the configuration file.
        overrides: Additional configuration overrides. Can be provided as a
            DictConfig, a regular dictionary, or a list of `key=value` strings (e.g.
            `["foo=1.0", "bar=baz"]`). Defaults to `None`.
        keep_targets: Whether to keep target fields needed for instantiation in the
            parsed config. Defaults to `True`.
        keep_meta: Whether to keep metadata fields in the parsed config. Defaults to
            `False`.

    Returns:
        The parsed configuration.
    """
    file_path = Path(file_path).resolve()
    config = OmegaConf.load(file_path)
    _resolve_imports(config, file_path, visited_paths={file_path})
    _merge_base_recursive(config)
    _resolve_defaults_recursive(config)
    if overrides is not None:
        overrides = _cast_overrides(overrides)
        config.merge_with(overrides)
    if keep_meta and keep_targets:
        return config
    exclude_keys = set()
    if not keep_meta:
        exclude_keys.add(META_KEY)
    if not keep_targets:
        exclude_keys.add(REF_KEY)
        exclude_keys.add(CLASS_KEY)
        exclude_keys.add(PARTIAL_KEY)
    _exclude_keys_recursive(config, exclude_keys)
    return config


def _cast_overrides(
    overrides: DictConfig | dict[str, Any] | list[str],
) -> DictConfig:
    if OmegaConf.is_config(overrides):
        return overrides
    elif isinstance(overrides, dict):
        return OmegaConf.create(overrides)
    elif isinstance(overrides, list):
        return OmegaConf.from_dotlist(overrides)
    raise ValueError(
        f"Unsupported overrides type: {type(overrides)}. Expected `Config`, `dict` "
        "or `list` of `key=value` string pairs."
    )


def _resolve_imports(
    config: DictConfig | ListConfig, config_path: Path, visited_paths: set[Path]
) -> None:
    cache: dict[Path, DictConfig | ListConfig] = {}
    if OmegaConf.is_list(config):
        for index in range(len(config)):
            node = config._get_node(index)
            if OmegaConf.is_config(node):
                _resolve_imports(node, config_path, visited_paths)
            else:
                value = node._value() if node is not None else None
                if isinstance(value, str) and value.startswith(IMPORT_KEY):
                    config[index] = _import_node(
                        config[index], config_path, visited_paths, cache
                    )
        return
    for key, value in config.items_ex(resolve=False):
        if OmegaConf.is_config(value):
            _resolve_imports(value, config_path, visited_paths)
        elif isinstance(value, str) and value.startswith(IMPORT_KEY):
            config[key] = _import_node(config[key], config_path, visited_paths, cache)


def _import_node(
    statement: str,
    config_path: Path,
    visited_paths: set[Path],
    cache: dict[Path, DictConfig | ListConfig],
) -> Any:
    # Match the pattern ~import <file_path>[#<node_path>]
    args = statement[len(IMPORT_KEY) :].strip().split("#")
    file_path = Path(args[0])
    if not file_path.is_absolute():
        file_path = Path(config_path.parent, file_path)
    file_path = file_path.resolve()
    node_path = args[1].strip() if len(args) > 1 else ""
    # Load the imported config file and resolve its own imports first
    if file_path in visited_paths:
        raise ValueError(
            f"Circular import detected: `{file_path}` was already imported."
        )
    if file_path in cache:
        imported_config = cache[file_path]
    else:
        imported_config = OmegaConf.load(file_path)
        _resolve_imports(
            imported_config,
            file_path,
            visited_paths={*visited_paths, file_path},
        )
        cache[file_path] = imported_config
    node = imported_config
    for part in filter(None, node_path.split(".")):
        if node is None:
            break
        node = (
            node._get_node(int(part))
            if OmegaConf.is_list(node)
            else node._get_node(part)
        )
    if node is None:
        raise ValueError(
            f"Import `{statement}` selects node `{node_path}`, which does not exist in "
            f"`{file_path}`."
        )
    return node


def _merge_base_recursive(config: DictConfig | ListConfig) -> None:
    if OmegaConf.is_list(config):
        for index in range(len(config)):
            item = config._get_node(index)
            if OmegaConf.is_config(item):
                _merge_base_recursive(item)
        return
    for _key, node in config.items_ex(resolve=False):
        if OmegaConf.is_dict(node) or OmegaConf.is_list(node):
            _merge_base_recursive(node)
    if config._get_node(BASE_KEY) is None:
        return
    base = config[BASE_KEY]
    # A base may be a single mapping or a list of mappings. Later list elements take
    # precedence over earlier ones, and the node's own keys take precedence over all.
    if OmegaConf.is_list(base):
        bases = [base[index] for index in range(len(base))]
        if not all(OmegaConf.is_dict(item) for item in bases):
            raise ValueError(
                f"List-valued `{BASE_KEY}` in parent `{config}` must contain only "
                f"dictionaries."
            )
    elif OmegaConf.is_dict(base):
        bases = [base]
    else:
        raise ValueError(
            f"Node `{BASE_KEY}` in parent `{config}` is not a dictionary or a list of "
            f"dictionaries."
        )
    config.pop(BASE_KEY)
    merged_config = OmegaConf.merge(*bases, config)
    for key in list(merged_config.keys()):
        config[key] = merged_config._get_node(key)
    return


def _resolve_defaults_recursive(config: DictConfig | ListConfig) -> None:
    if OmegaConf.is_list(config):
        for index in range(len(config)):
            item = config._get_node(index)
            if OmegaConf.is_config(item):
                _resolve_defaults_recursive(item)
        return
    for _key, node in config.items_ex(resolve=False):
        if OmegaConf.is_dict(node) or OmegaConf.is_list(node):
            _resolve_defaults_recursive(node)
    if config._get_node(DEFAULTS_KEY) is None:
        return
    defaults = config[DEFAULTS_KEY]
    if not OmegaConf.is_dict(defaults):
        raise ValueError(
            f"Node `{DEFAULTS_KEY}` in parent `{config}` is not a dictionary."
        )
    config.pop(DEFAULTS_KEY)
    for key in list(config.keys()):
        if str(key).startswith("$"):
            continue
        item = config._get_node(key)
        if OmegaConf.is_dict(item):
            config[key] = OmegaConf.merge(defaults, item)


def _exclude_keys_recursive(config: DictConfig | ListConfig, exclude: set[str]) -> None:
    if OmegaConf.is_list(config):
        for index in range(len(config)):
            node = config._get_node(index)
            if OmegaConf.is_config(node):
                _exclude_keys_recursive(node, exclude)
        return
    for key, node in list(config.items_ex(resolve=False)):
        if key in exclude:
            config.pop(key)
        elif OmegaConf.is_config(node):
            _exclude_keys_recursive(node, exclude)
