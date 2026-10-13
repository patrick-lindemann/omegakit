from importlib.metadata import version

from ._core.error import OmegaKitBaseException
from ._core.features.base import BASE_KEY, BaseTypeError, ConfigInheritanceError
from ._core.features.each import EACH_KEY, ConfigEachError, EachTypeError
from ._core.features.include import (
    INCLUDE_PREFIX,
    ConfigIncludeError,
    IncludeCycleError,
    IncludeInterpolationError,
    IncludeMissingValueError,
    IncludeNodeNotFoundError,
    IncludeRootError,
    IncludeSyntaxError,
    IncludeTypeError,
)
from ._core.features.meta import META_KEY
from ._core.features.overrides import (
    ConfigOverrideError,
    OverrideMergeError,
    OverrideSyntaxError,
    OverrideTypeError,
)
from ._core.features.symbol import (
    SYMBOL_KEY,
    ConfigSymbolError,
    SymbolInterpolationError,
    SymbolMissingValueError,
    SymbolSyntaxError,
    SymbolTypeError,
)
from ._core.features.target import (
    ARGS_KEY,
    PARTIAL_KEY,
    TARGET_KEY,
    ConfigTargetError,
    TargetInterpolationError,
    TargetMissingValueError,
    TargetSyntaxError,
    TargetTypeError,
    make_node,
)
from ._core.utils.file import (
    ConfigFileNotFoundError,
    ConfigFilePermissionError,
    ConfigSyntaxError,
)
from ._core.utils.locate import QualifiedNameNotFoundError, QualifiedNameSyntaxError
from ._core.utils.merge import ConfigMergeError, MergeCycleError, MergeReferenceError
from ._core.utils.walk import walk
from .config import Config
from .configurable import Configurable
from .instantiate import instantiate, prepare
from .load import ConfigLoadError, LoadTypeError, load_config
from .schema import (
    ConfigSchemaError,
    SchemaDefinitionError,
    SchemaKeyError,
    SchemaMissingValueError,
    SchemaTypeError,
    SchemaValueError,
)
from .validate import (
    ConfigValidationError,
    ValidationCycleError,
    ValidationInterpolationError,
    ValidationMissingValueError,
    ValidationSyntaxError,
    validate,
)

__version__ = version("omegakit")

__all__ = [
    "ARGS_KEY",
    "BASE_KEY",
    "EACH_KEY",
    "INCLUDE_PREFIX",
    "META_KEY",
    "PARTIAL_KEY",
    "SYMBOL_KEY",
    "TARGET_KEY",
    "BaseTypeError",
    "Config",
    "ConfigEachError",
    "ConfigFileNotFoundError",
    "ConfigFilePermissionError",
    "ConfigIncludeError",
    "ConfigInheritanceError",
    "ConfigLoadError",
    "ConfigMergeError",
    "ConfigOverrideError",
    "ConfigSchemaError",
    "ConfigSymbolError",
    "ConfigSyntaxError",
    "ConfigTargetError",
    "ConfigValidationError",
    "Configurable",
    "EachTypeError",
    "IncludeCycleError",
    "IncludeInterpolationError",
    "IncludeMissingValueError",
    "IncludeNodeNotFoundError",
    "IncludeRootError",
    "IncludeSyntaxError",
    "IncludeTypeError",
    "LoadTypeError",
    "MergeCycleError",
    "MergeReferenceError",
    "OmegaKitBaseException",
    "OverrideMergeError",
    "OverrideSyntaxError",
    "OverrideTypeError",
    "QualifiedNameNotFoundError",
    "QualifiedNameSyntaxError",
    "SchemaDefinitionError",
    "SchemaKeyError",
    "SchemaMissingValueError",
    "SchemaTypeError",
    "SchemaValueError",
    "SymbolInterpolationError",
    "SymbolMissingValueError",
    "SymbolSyntaxError",
    "SymbolTypeError",
    "TargetInterpolationError",
    "TargetMissingValueError",
    "TargetSyntaxError",
    "TargetTypeError",
    "ValidationCycleError",
    "ValidationInterpolationError",
    "ValidationMissingValueError",
    "ValidationSyntaxError",
    "instantiate",
    "load_config",
    "make_node",
    "prepare",
    "validate",
    "walk",
]
