import sys


def add_note(error: BaseException, note: str) -> None:
    """Add a note to an error, also on Python 3.10.

    Args:
        error: The error.
        note: The note.
    """
    if sys.version_info >= (3, 11):
        error.add_note(note)
    else:
        # Python 3.10 has no `add_note`, which only appends to `__notes__`
        vars(error).setdefault("__notes__", []).append(note)
