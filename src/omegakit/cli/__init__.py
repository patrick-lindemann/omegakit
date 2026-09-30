from ._arg import Arguments
from ._routine import Routine
from .check import CheckArguments, CheckRoutine
from .show import ShowArguments, ShowRoutine

ROUTINES: frozenset[Routine] = frozenset({CheckRoutine(), ShowRoutine()})

__all__ = [
    "ROUTINES",
    "Arguments",
    "CheckArguments",
    "CheckRoutine",
    "Routine",
    "ShowArguments",
    "ShowRoutine",
]
