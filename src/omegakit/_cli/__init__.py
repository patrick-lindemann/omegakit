from ._routine import Arguments, Routine
from .check import CheckArguments, CheckRoutine
from .show import ShowArguments, ShowRoutine

ROUTINES: tuple[Routine, ...] = (CheckRoutine(), ShowRoutine())

__all__ = [
    "ROUTINES",
    "Arguments",
    "CheckArguments",
    "CheckRoutine",
    "Routine",
    "ShowArguments",
    "ShowRoutine",
]
