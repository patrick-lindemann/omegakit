import itertools

import pytest
from omegaconf import OmegaConf

from omegakit.resolvers import register_resolver


def test_register_resolver_registers_a_resolver():
    register_resolver("double", lambda value: value * 2)
    assert OmegaConf.create({"x": "${double:3}"}).x == 6


def test_register_resolver_caches_results_per_config():
    counter = itertools.count(1)
    register_resolver("count", lambda: next(counter))
    config = OmegaConf.create({"a": "${count:}", "b": "${count:}"})
    assert (config.a, config.b) == (1, 1)
    assert OmegaConf.create({"a": "${count:}"}).a == 2


def test_register_resolver_refuses_a_taken_name_unless_replacing():
    register_resolver("answer", lambda: 1)
    with pytest.raises(ValueError, match="answer"):
        register_resolver("answer", lambda: 2)
    register_resolver("answer", lambda: 2, replace=True)
    assert OmegaConf.create({"x": "${answer:}"}).x == 2
