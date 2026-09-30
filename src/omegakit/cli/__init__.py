from ._arg import Arguments
from ._routine import Routine
from .check import CheckArguments, CheckRoutine
from .export_schema import ExportSchemaArguments, ExportSchemaRoutine
from .show import ShowArguments, ShowRoutine

ROUTINES: frozenset[Routine] = frozenset(
    {CheckRoutine(), ExportSchemaRoutine(), ShowRoutine()}
)

__all__ = [
    "ROUTINES",
    "Arguments",
    "CheckArguments",
    "CheckRoutine",
    "ExportSchemaArguments",
    "ExportSchemaRoutine",
    "Routine",
    "ShowArguments",
    "ShowRoutine",
]
