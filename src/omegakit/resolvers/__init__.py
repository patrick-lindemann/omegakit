# No individual resolver exports here since some of them depend on optional third-party
# packages

from ._register import register_resolver

__all__ = ["register_resolver"]
