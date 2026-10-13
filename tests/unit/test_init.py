import omegakit
from omegakit._core import errors


def test_every_exported_name_exists():
    for name in omegakit.__all__:
        assert hasattr(omegakit, name)


def test_entry_points_are_exported():
    names = {
        "Configurable",
        "instantiate",
        "load_config",
        "make_node",
        "prepare",
        "validate",
    }
    assert names <= set(omegakit.__all__)


def test_every_error_is_exported():
    error_types = [
        value
        for value in vars(errors).values()
        if isinstance(value, type) and issubclass(value, errors.OmegaKitBaseException)
    ]
    assert error_types
    for error_type in error_types:
        assert getattr(omegakit, error_type.__name__) is error_type
        assert error_type.__name__ in omegakit.__all__
