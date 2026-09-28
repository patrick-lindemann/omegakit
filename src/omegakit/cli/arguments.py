from pathlib import Path


def split_arguments(arguments: list[str]) -> tuple[list[Path], list[str]]:
    """Split command-line arguments into config paths and `key=value` overrides.

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
