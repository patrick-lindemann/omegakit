import contextlib
import dataclasses
import re
import types
import typing
from collections.abc import Callable, Iterable
from typing import Any, TypeAliasType, cast, get_args, get_origin

from omegaconf import MISSING, DictConfig, ListConfig, Node, OmegaConf
from omegaconf.errors import (
    InterpolationKeyError,
    InterpolationToMissingValueError,
    MissingMandatoryValue,
    OmegaConfBaseException,
)

from ._keys import CLASS_KEY, META_KEY, PARTIAL_KEY, REF_KEY
from ._schema import (
    ConfigValidationError,
    check_schema,
    classify_fields,
    find_schema,
    find_section,
    validate_native,
)
from ._utils import describe_value, format_path, import_object

SECRET_WORDS = (
    ("password",),
    ("passwd",),
    ("pass",),
    ("passphrase",),
    ("secret",),
    ("token",),
    ("credential",),
    ("auth",),
    ("bearer",),
    ("cookie",),
    ("dsn",),
    ("webhook",),
    ("apikey",),
    ("api", "key"),
    ("private", "key"),
    ("access", "key"),
)
_WORD = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+")
_ENV_NAME = re.compile(r"\$\{\s*oc\.env\s*:\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)")
_MASK = "***"


def validate(
    config: DictConfig | dict[str, Any],
    *,
    schema: type | None = None,
    allow_missing: bool = False,
    allowed_modules: Iterable[str] | None = None,
) -> None:
    """Check a loaded config against the schemas of the classes it names.

    The config is resolved, and every node with `$class` is checked bottom-up against
    the schema of its class. An object field accepts a node whose `$class` is the
    field's class or a subclass, or a `$ref` to an instance of it.

    Validation checks values. It calls no `$class` target and constructs none of the
    schema's dataclasses. Code still runs: the modules named by `$class` and `$ref`
    are imported, resolvers run, so do `__instancecheck__` and `__subclasscheck__`
    of imported classes, and every `default_factory` of a schema runs, possibly
    several times and even for fields that the config sets. An exception from a
    factory propagates.

    Args:
        config: The assembled config, such as the result of `load_config`.
        schema: The class the root of the config must match. A dataclass checks the
            root as a section. Another class checks the root as a node that builds
            it: with `$class`, that class must be `schema` or a subclass; without,
            the root is checked against the schema of `schema`. Defaults to `None`.
        allow_missing: Accept missing values: `???`, required fields that are not
            given, and interpolations to missing or unknown keys, as in a library
            file that its consumers complete. Defaults to `False`.
        allowed_modules: The modules that `$class` and `$ref` may name. An entry
            allows that module and its submodules, and an object is also checked
            against the module it is defined in. `[]` allows none. It limits which
            modules a config can name; it is not a sandbox. Defaults to `None`,
            which allows every module.

    Raises:
        ConfigValidationError: If the config cannot be resolved, does not match a
            schema, or names a module that is not allowed.
        TypeError: If `schema` is not a class, or `allowed_modules` is a string.
    """  # noqa: DOC502
    if not isinstance(config, DictConfig):
        config = OmegaConf.create(config)
    plain_config = resolve_config(config, allow_missing=allow_missing)
    check_resolved(
        plain_config,
        schema=schema,
        allow_missing=allow_missing,
        allowed_modules=allowed_modules,
    )


def resolve_config(
    config: DictConfig | ListConfig, *, allow_missing: bool = False
) -> Any:
    """Resolve a config into plain containers.

    Args:
        config: The config to resolve.
        allow_missing: Give `???` for missing values and for interpolations to
            missing or unknown keys, instead of raising. Defaults to `False`.

    Returns:
        The resolved config as `dict`s and `list`s.

    Raises:
        ConfigValidationError: If a value is missing or an interpolation fails,
            including an exception from a resolver. OmegaConf's error is the cause.
    """
    try:
        if not allow_missing:
            return OmegaConf.to_container(config, resolve=True, throw_on_missing=True)
        return _resolve_allowing_missing(config)
    except OmegaConfBaseException as error:
        location = f" `{error.full_key}`" if error.full_key else " the config"
        raise ConfigValidationError(
            f"Cannot resolve{location}: {str(error).splitlines()[0]}"
        ) from error


def mask_secrets(config: DictConfig, *, keys: Iterable[str] = ()) -> Any:
    """Resolve a config for logging, with its secrets masked.

    Give it the unresolved config from `load_config`: a resolved config no longer
    shows which values come from environment variables. A value is masked as `***`
    when its key, or a key above it, contains a secret word such as `password`,
    `token`, `secret` or `api_key`, and when it reads a secret-named environment
    variable with `${oc.env:...}`. Keys are split into words at `_`, `-`, `.` and
    camelCase, so `pad_token` is masked and `tokenizer` is not. The masked strings
    of 8 or more characters are also replaced by `***` inside every other string,
    such as a password inside a URL. Missing values print as `???`.

    It cannot see a secret in a value whose key names no secret, a secret shorter
    than 8 characters used elsewhere, a secret used as a key, or one read by a
    resolver other than `oc.env`. A secret equal to a common word masks that word
    everywhere. Objects built by `instantiate` are not masked.

    Args:
        config: The unresolved config, such as the result of `load_config`.
        keys: More secret words, added to the defaults. An entry is a lowercase
            word, or several words separated by spaces that must appear in that
            order, such as `"client secret"`. Defaults to `()`.

    Returns:
        The resolved config as plain dictionaries and lists, with secrets masked.

    Raises:
        ConfigValidationError: If an interpolation outside the masked values fails.
    """  # noqa: DOC502
    words = (
        *SECRET_WORDS,
        *(tuple(key.lower().split()) for key in keys if key.strip()),
    )
    return mask_node(config, words, resolve=True)


def mask_node(node: Node, words: tuple[tuple[str, ...], ...], *, resolve: bool) -> Any:
    """Mask the secrets in one node of a config, as `mask_secrets` does.

    The secrets are found in the whole config, and the keys above `node` count, but
    only `node` is resolved.

    Args:
        node: The node, in the unresolved config.
        words: The secret words, each a tuple of lowercase words.
        resolve: Resolve `node`, mask by environment variable and by value. Without
            it, only keys are checked and interpolations stay as written.

    Returns:
        The node as plain dictionaries, lists and values, with secrets masked.

    Raises:
        ConfigValidationError: If an interpolation outside the masked values fails.
    """
    secrets: set[str] = set()
    masked = False
    current: Any = node
    while current is not None:
        key = current._key()
        masked = masked or (isinstance(key, str) and _is_secret(key, words))
        current = current._get_parent()
    try:
        if resolve:
            _collect(cast(Any, node._get_root()), words, False, secrets)
        if isinstance(node, (DictConfig, ListConfig)) and not (
            node._is_missing() or node._is_interpolation()
        ):
            value = _view(node, words, masked, resolve)
        else:
            value = _leaf(
                node._get_parent_container(), node._key(), words, masked, resolve
            )
    except OmegaConfBaseException as error:
        location = f" `{error.full_key}`" if error.full_key else " the config"
        raise ConfigValidationError(
            f"Cannot resolve{location}: {str(error).splitlines()[0]}"
        ) from error
    return _replace(value, sorted(secrets, key=len, reverse=True))


def check_resolved(
    config: Any,
    *,
    schema: type | None = None,
    allow_missing: bool = False,
    allowed_modules: Iterable[str] | None = None,
) -> None:
    """Check a resolved config, the plain containers of `resolve_config`.

    Args:
        config: The resolved config.
        schema: The class the root must match, as in `validate`. Defaults to `None`.
        allow_missing: Accept missing values, as in `validate`. Defaults to `False`.
        allowed_modules: The modules that `$class` and `$ref` may name, as in
            `validate`. Defaults to `None`.

    Raises:
        TypeError: If `schema` is not a class, or `allowed_modules` is a string.
        ConfigValidationError: If the config does not match a schema.
    """
    if isinstance(allowed_modules, str):
        raise TypeError(
            f"`allowed_modules` must be a list of module names, not the string "
            f"`{allowed_modules!r}`."
        )
    if allowed_modules is not None:
        allowed_modules = tuple(allowed_modules)
    if schema is None:
        _check_untyped(config, (), allow_missing, allowed_modules)
        return
    if not isinstance(schema, type):
        raise TypeError(f"`{schema!r}` is not a class.")
    if (
        isinstance(config, dict)
        and CLASS_KEY not in config
        and not dataclasses.is_dataclass(schema)
    ):
        section = find_schema(schema)
        if section is None:
            raise ConfigValidationError(
                f"The root has no `{CLASS_KEY}`, and `{schema.__qualname__}` has no "
                "dataclass schema to check it against."
            )
        _check_target(schema, config, (), allow_missing, allowed_modules)
        return
    _check_object(config, schema, (), allow_missing, allowed_modules)


def _resolve_allowing_missing(container: DictConfig | ListConfig) -> Any:
    if isinstance(container, ListConfig):
        return [resolve_item(container, index) for index in range(len(container))]
    return {key: resolve_item(container, key) for key in container}


def resolve_item(container: Any, key: Any) -> Any:
    """Resolve one item of a container, giving `???` for a missing value.

    Args:
        container: The `DictConfig` or `ListConfig`.
        key: The item's key or index.

    Returns:
        The resolved item, with containers as `dict`s and `list`s, or `???` for a
        missing value and for an interpolation to a missing or unknown key.
    """
    try:
        value = container[key]
    except (
        MissingMandatoryValue,
        InterpolationToMissingValueError,
        InterpolationKeyError,
    ):
        return MISSING
    if isinstance(value, (DictConfig, ListConfig)):
        return _resolve_allowing_missing(value)
    return value


def _view(
    container: DictConfig | ListConfig,
    words: tuple[tuple[str, ...], ...],
    masked: bool,
    resolve: bool,
) -> Any:
    key: Any
    result = {}
    for key in (
        range(len(container)) if isinstance(container, ListConfig) else container
    ):
        node = container._get_node(key)
        secret = masked or (isinstance(key, str) and _is_secret(key, words))
        if isinstance(node, (DictConfig, ListConfig)) and not (
            node._is_missing() or node._is_interpolation()
        ):
            result[key] = _view(node, words, secret, resolve)
        else:
            result[key] = _leaf(container, key, words, secret, resolve)
    return list(result.values()) if isinstance(container, ListConfig) else result


def _leaf(
    container: Any,
    key: Any,
    words: tuple[tuple[str, ...], ...],
    secret: bool,
    resolve: bool,
) -> Any:
    raw = container._get_node(key)._value()
    if raw == MISSING:
        return MISSING
    if resolve and _reads_secret(raw, words):
        secret = True
    if secret:
        return _MASK
    return resolve_item(container, key) if resolve else raw


def _collect(
    container: DictConfig | ListConfig,
    words: tuple[tuple[str, ...], ...],
    masked: bool,
    secrets: set[str],
) -> None:
    key: Any
    for key in (
        range(len(container)) if isinstance(container, ListConfig) else container
    ):
        node = container._get_node(key)
        secret = masked or (isinstance(key, str) and _is_secret(key, words))
        if isinstance(node, (DictConfig, ListConfig)) and not (
            node._is_missing() or node._is_interpolation()
        ):
            _collect(node, words, secret, secrets)
        elif secret or (isinstance(node, Node) and _reads_secret(node._value(), words)):
            # A secret that cannot be resolved is masked all the same.
            with contextlib.suppress(OmegaConfBaseException):
                value = resolve_item(container, key)
                if isinstance(value, str) and len(value) >= 8:
                    secrets.add(value)


def _reads_secret(raw: Any, words: tuple[tuple[str, ...], ...]) -> bool:
    return isinstance(raw, str) and any(
        _is_secret(name, words) for name in _ENV_NAME.findall(raw)
    )


def _is_secret(key: str, words: tuple[tuple[str, ...], ...]) -> bool:
    parts = [word.lower() for word in _WORD.findall(key)]
    for entry in words:
        for start in range(len(parts) - len(entry) + 1):
            *head, last = parts[start : start + len(entry)]
            if tuple(head) == entry[:-1] and last in (
                entry[-1],
                f"{entry[-1]}s",
                f"{entry[-1]}es",
            ):
                return True
    return False


def _replace(value: Any, secrets: list[str]) -> Any:
    if isinstance(value, dict):
        return {key: _replace(item, secrets) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace(item, secrets) for item in value]
    if isinstance(value, str):
        for secret in secrets:
            value = value.replace(secret, _MASK)
    return value


def _check_untyped(
    value: Any,
    path: tuple[str | int, ...],
    allow_missing: bool,
    allowed_modules: tuple[str, ...] | None,
) -> None:
    if isinstance(value, list):
        for index, item in enumerate(value):
            _check_untyped(item, (*path, index), allow_missing, allowed_modules)
        return
    if not isinstance(value, dict):
        return
    value = {key: item for key, item in value.items() if key != META_KEY}
    if CLASS_KEY in value:
        _check_class_node(value, path, allow_missing, allowed_modules)
    elif REF_KEY in value:
        _import_ref(value, path, allowed_modules)
    else:
        for key, item in value.items():
            if isinstance(key, str) and key.startswith("$"):
                raise ConfigValidationError(
                    f"Key `{key}` in `{format_path(path)}` is not supported here; keys "
                    "starting with `$` are reserved."
                )
            _check_untyped(item, (*path, key), allow_missing, allowed_modules)


def _check_class_node(
    node: dict[str, Any],
    path: tuple[str | int, ...],
    allow_missing: bool,
    allowed_modules: tuple[str, ...] | None,
) -> Any:
    target = _import(node, CLASS_KEY, path, allowed_modules)
    if not (callable(target) or hasattr(target, "from_config")):
        raise ConfigValidationError(
            f"`{CLASS_KEY}: {node[CLASS_KEY]}` in `{format_path(path)}` is neither "
            f"callable nor has `from_config`. Use `{REF_KEY}` for an object that is "
            "used as it is."
        )
    _check_target(target, node, path, allow_missing, allowed_modules)
    return target


def _check_target(
    target: Any,
    node: dict[str, Any],
    path: tuple[str | int, ...],
    allow_missing: bool,
    allowed_modules: tuple[str, ...] | None,
) -> None:
    values = {}
    for key, value in node.items():
        if key in (CLASS_KEY, META_KEY):
            continue
        if key == PARTIAL_KEY:
            if not isinstance(value, bool):
                raise ConfigValidationError(
                    f"`{PARTIAL_KEY}` in `{format_path(path)}` must be `true` or "
                    f"`false`, got {describe_value(value)}."
                )
            continue
        if isinstance(key, str) and key.startswith("$"):
            raise ConfigValidationError(
                f"Key `{key}` in `{format_path(path)}` is not supported next to "
                f"`{CLASS_KEY}`; keys starting with `$` are reserved."
            )
        values[key] = value
    schema = find_schema(target) if isinstance(target, type) else None
    if schema is None:
        for key, value in values.items():
            _check_untyped(value, (*path, key), allow_missing, allowed_modules)
    else:
        check_schema(target)
        _check_section(schema, values, path, allow_missing, allowed_modules)


def _check_section(
    schema: type,
    values: dict[str, Any],
    path: tuple[str | int, ...],
    allow_missing: bool,
    allowed_modules: tuple[str, ...] | None,
) -> None:
    for name, (kind, annotation) in classify_fields(schema).items():
        if name not in values or kind == "native":
            continue
        if kind == "any":
            _check_untyped(values[name], (*path, name), allow_missing, allowed_modules)
        else:
            _check_object(
                values[name], annotation, (*path, name), allow_missing, allowed_modules
            )
    validate_native(schema, values, path, allow_missing)


def _check_object(
    value: Any,
    annotation: Any,
    path: tuple[str | int, ...],
    allow_missing: bool,
    allowed_modules: tuple[str, ...] | None,
) -> None:
    if allow_missing and value == MISSING:
        return
    while isinstance(annotation, TypeAliasType):
        annotation = annotation.__value__
    if get_origin(annotation) in (typing.Union, types.UnionType):
        members = get_args(annotation)
    else:
        members = (annotation,)
    classes = tuple(
        member.__value__ if isinstance(member, TypeAliasType) else member
        for member in members
        if member is not type(None)
    )
    if value is None:
        if type(None) in members:
            return
        _check_type(isinstance, None, classes, path, "`None`")
        return
    if len(classes) == 1 and get_origin(classes[0]) in (list, dict):
        item_annotation = get_args(classes[0])[-1]
        if get_origin(classes[0]) is list and isinstance(value, list):
            for index, item in enumerate(value):
                _check_object(
                    item,
                    item_annotation,
                    (*path, index),
                    allow_missing,
                    allowed_modules,
                )
            return
        if (
            get_origin(classes[0]) is dict
            and isinstance(value, dict)
            and CLASS_KEY not in value
            and REF_KEY not in value
        ):
            _check_untyped(
                {key: None for key in value}, path, allow_missing, allowed_modules
            )
            for key, item in value.items():
                if key != META_KEY:
                    _check_object(
                        item,
                        item_annotation,
                        (*path, key),
                        allow_missing,
                        allowed_modules,
                    )
            return
        raise ConfigValidationError(
            f"`{format_path(path)}` expects `{classes[0]}`, but the config gives "
            f"{describe_value(value)}."
        )
    if isinstance(value, dict):
        value = {key: item for key, item in value.items() if key != META_KEY}
        if CLASS_KEY in value:
            target = _check_class_node(value, path, allow_missing, allowed_modules)
            if value.get(PARTIAL_KEY) is not True and isinstance(target, type):
                _check_type(
                    issubclass, target, classes, path, f"`$class: {value[CLASS_KEY]}`"
                )
            return
        if REF_KEY in value:
            target = _import_ref(value, path, allowed_modules)
            _check_type(isinstance, target, classes, path, f"`$ref: {value[REF_KEY]}`")
            return
        section = find_section(annotation)
        if section is not None:
            _check_section(section, value, path, allow_missing, allowed_modules)
            return
        _check_type(isinstance, value, classes, path, "a mapping without `$class`")
        _check_untyped(value, path, allow_missing, allowed_modules)
        return
    _check_type(isinstance, value, classes, path, describe_value(value))
    _check_untyped(value, path, allow_missing, allowed_modules)


def _check_type(
    check: Callable[[Any, tuple[Any, ...]], bool],
    value: Any,
    classes: tuple[Any, ...],
    path: tuple[str | int, ...],
    given: str,
) -> None:
    if not all(isinstance(member, type) for member in classes):
        return
    try:
        valid = check(value, classes)
    except TypeError:
        return
    if not valid:
        expected = " | ".join(member.__qualname__ for member in classes)
        raise ConfigValidationError(
            f"`{format_path(path)}` expects {expected}, but the config gives {given}."
        )


def _import_ref(
    node: dict[str, Any],
    path: tuple[str | int, ...],
    allowed_modules: tuple[str, ...] | None,
) -> Any:
    if len(node) > 1:
        raise ConfigValidationError(
            f"A node using `{REF_KEY}` cannot contain any other keys, but "
            f"`{format_path(path)}` has {', '.join(map(repr, node))}."
        )
    return _import(node, REF_KEY, path, allowed_modules)


def _import(
    node: dict[str, Any],
    key: str,
    path: tuple[str | int, ...],
    allowed_modules: tuple[str, ...] | None,
) -> Any:
    import_path = node[key]
    if not isinstance(import_path, str):
        raise ConfigValidationError(
            f"`{key}` in `{format_path(path)}` must be an import path, such as "
            "`package.module.Name`, but the config gives "
            f"{describe_value(import_path)}."
        )
    # Checked before the import, so that a module that is not allowed never runs.
    if not _is_allowed(import_path.rpartition(".")[0], allowed_modules):
        raise ConfigValidationError(
            f"`{key}: {import_path}` in `{format_path(path)}` names a module that "
            "is not in `allowed_modules`."
        )
    try:
        target = import_object(import_path)
    except ImportError as error:
        # A module that the target's own module fails to import is a missing
        # dependency, not a mistake in the config.
        parts = import_path.split(".")
        targets = {".".join(parts[:end]) for end in range(1, len(parts))}
        if error.name != import_path and not (
            isinstance(error, ModuleNotFoundError) and error.name in targets
        ):
            raise
        raise ConfigValidationError(
            f"Cannot import `{import_path}` in `{format_path(path)}`: {error}"
        ) from error
    # An allowed module can import a name from a module that is not allowed.
    module = getattr(target, "__module__", None)
    if isinstance(module, str) and not _is_allowed(module, allowed_modules):
        raise ConfigValidationError(
            f"`{key}: {import_path}` in `{format_path(path)}` is defined in "
            f"`{module}`, which is not in `allowed_modules`."
        )
    return target


def _is_allowed(module: str, allowed_modules: tuple[str, ...] | None) -> bool:
    return allowed_modules is None or any(
        module == allowed or module.startswith(f"{allowed}.")
        for allowed in allowed_modules
    )
