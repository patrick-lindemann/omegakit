import importlib
import inspect
import os
from collections.abc import Callable, Iterator
from typing import Any

import yaml
from omegaconf import DictConfig, ListConfig, OmegaConf

from .keys import CLASS_KEY


def walk(config: DictConfig | ListConfig) -> Iterator[DictConfig]:
    """Walk along every mapping node in `config` depth-first.

    Args:
        config: The config to traverse.

    Yields:
        Each mapping node, parents before children.
    """
    if isinstance(config, DictConfig):
        yield config
        children = [node for _, node in config.items_ex(resolve=False)]
    else:
        children = [config._get_node(index) for index in range(len(config))]
    for node in children:
        if isinstance(node, (DictConfig, ListConfig)):
            yield from walk(node)


def walk_post_order(config: DictConfig | ListConfig) -> Iterator[DictConfig]:
    """Walk along every mapping node in `config` depth-first, children first.

    Args:
        config: The config to traverse.

    Yields:
        Each mapping node, children before parents.
    """
    if isinstance(config, DictConfig):
        children = [node for _, node in config.items_ex(resolve=False)]
    else:
        children = [config._get_node(index) for index in range(len(config))]
    for node in children:
        if isinstance(node, (DictConfig, ListConfig)):
            yield from walk_post_order(node)
    if isinstance(config, DictConfig):
        yield config


def make_node(target: Callable[..., Any], /, **kwargs: Any) -> dict[str, Any]:
    """Create an instantiable config node for a class or function.

    Use it inside `from_config` for children that code chooses, such as
    `instantiate(make_node(Postgres, pool_size=5), schema=Postgres)`.

    Args:
        target: The class or function to build. It must be defined at module level.
        **kwargs: The node's arguments.

    Returns:
        The node: `kwargs` plus `$class` set to the import path of `target`.

    Raises:
        ValueError: If `target` is defined inside a function or a class, where it
            cannot be imported by its path.
    """
    qualname = target.__qualname__
    if "." in qualname:
        raise ValueError(
            f"Cannot create a node for `{qualname}`: only objects defined at module "
            "level can be imported by their path."
        )
    return {CLASS_KEY: f"{target.__module__}.{qualname}", **kwargs}


def format_path(path: tuple[str | int, ...]) -> str:
    """Format a node path from the config root, such as `items.0.model`.

    Args:
        path: The keys and list indices from the root.

    Returns:
        The dotted path, or `<root>` for the root itself.
    """
    return ".".join(map(str, path)) or "<root>"


def describe_value(value: Any) -> str:
    """Describe a config value for an error message, without a container's items.

    Args:
        value: The value.

    Returns:
        The `repr` of a scalar in backticks, the keys of a mapping, or the length of a
        list.
    """
    if isinstance(value, dict):
        keys = ", ".join(f"`{key}`" for key in value)
        return f"a mapping with keys {keys}" if keys else "an empty mapping"
    if isinstance(value, (list, tuple)):
        return f"a list of {len(value)} items"
    return f"`{value!r}`"


def describe_error(error: Exception) -> str:
    """Describe an error from PyYAML, OmegaConf or Python in one line.

    Args:
        error: The error.

    Returns:
        PyYAML's problem with its context and position, or the first line of the
        message of any other error.
    """
    if isinstance(error, yaml.MarkedYAMLError):
        context = f"{error.context}: " if error.context else ""
        mark = error.problem_mark
        position = f" (line {mark.line + 1}, column {mark.column + 1})" if mark else ""
        return f"{context}{error.problem}{position}"
    lines = str(error).splitlines()
    return lines[0] if lines else type(error).__name__


def import_object(import_path: str) -> Any:
    """Import an object by its dotted path, such as `package.module.Name`.

    Args:
        import_path: The module path and attribute name, separated by a dot.

    Returns:
        The imported object.

    Raises:
        ImportError: If `import_path` is not a dotted path of at least two names, if
            the module cannot be imported, or if it has no attribute of that name.
            The first and the last carry `import_path` as their `name`.
    """
    if not all(import_path.split(".")) or "." not in import_path:
        raise ImportError(
            f"`{import_path}` is not an import path of the form `package.module.Name`.",
            name=import_path,
        )
    module_path, _, attr_name = import_path.rpartition(".")
    module = importlib.import_module(module_path)
    try:
        return getattr(module, attr_name)
    except AttributeError as error:
        raise ImportError(
            f"Could not import `{attr_name}` from module `{module_path}`. Make sure "
            "the import name is correct, and that dependencies are installed, if "
            "necessary.",
            name=import_path,
        ) from error


def register_resolver(
    name: str, resolver: Callable[..., Any], *, replace: bool = False
) -> None:
    """Register a cached OmegaConf resolver on every supported OmegaConf version.

    OmegaConf 2.4 registers with `register_resolver` and deprecates
    `register_new_resolver`; 2.3 has only `register_new_resolver`, and its
    `register_resolver` is an older, incompatible function.

    Args:
        name: The resolver name, as used in `${name:...}`.
        resolver: The resolver function.
        replace: Replace a resolver of the same name. Defaults to `False`.
    """
    register: Any = OmegaConf.register_resolver
    if "replace" in inspect.signature(register).parameters:
        register(
            name,
            resolver,
            replace=replace,
            use_cache=True,
            annotation_validation="off",
        )
    else:
        OmegaConf.register_new_resolver(name, resolver, replace=replace, use_cache=True)


# The values that `${secret:...}` has given in this process, so that the command
# line can mask them wherever they appear.
SECRET_VALUES: set[str] = set()


def read_secret(name: str) -> str:
    """Read the environment variable of `${secret:NAME}`, and remember its value.

    Args:
        name: The name of the environment variable.

    Returns:
        The value of the variable.

    Raises:
        ValueError: If the variable is not set.
    """
    try:
        value = os.environ[name]
    except KeyError:
        raise ValueError(f"Environment variable `{name}` is not set.") from None
    SECRET_VALUES.add(value)
    return value
