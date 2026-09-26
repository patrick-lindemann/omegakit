from pathlib import Path


def split_arguments(arguments: list[str]) -> tuple[list[Path], list[str]]:
    """Split command-line arguments into config paths and `key=value` overrides.

    An argument that names an existing file is a path, even if it contains `=`.
    Otherwise it is an override if it has a `=` with no `/` before it, and a path
    (which then fails to load) if not. The order does not matter, so tools that
    append file names, such as pre-commit, work.

    Args:
        arguments: The positional arguments.

    Returns:
        The config paths and the overrides, each in their given order.
    """
    paths = []
    overrides = []
    for argument in arguments:
        key, separator, _ = argument.partition("=")
        if not Path(argument).exists() and separator and "/" not in key:
            overrides.append(argument)
        else:
            paths.append(Path(argument))
    return paths, overrides
