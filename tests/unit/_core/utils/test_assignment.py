import dataclasses

import pytest
from omegaconf import OmegaConf

from omegakit._core.utils.assignment import Assignment


def test_assignment_holds_what_is_written_where():
    config = OmegaConf.create({"model": {"depth": 2}})
    assignment = Assignment(config.model, "depth", 3)
    assignment.parent[assignment.key] = assignment.value
    assert config == {"model": {"depth": 3}}


def test_assignment_cannot_be_changed():
    config = OmegaConf.create({"depth": 2})
    assignment = Assignment(config, "depth", 3)
    with pytest.raises(dataclasses.FrozenInstanceError):
        assignment.value = 4  # pyright: ignore[reportAttributeAccessIssue]
