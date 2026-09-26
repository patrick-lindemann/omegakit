from functools import partial
from pathlib import Path

from shop import Cart

from omegakit import instantiate, load_config, prepare

config = load_config(Path(__file__).parent / "cart.yaml")

# `$class` nodes are built children first; `$ref` imports without calling.
cart = instantiate(config.cart, Cart)
assert [item.name for item in cart.items] == ["book", "pen"]
assert cart.total() == 14.0

# `prepare` defers the top-level call. Call-time arguments win over the config.
make_cart = prepare(config.cart, Cart)
assert isinstance(make_cart, partial)
assert make_cart(owner="ada").owner == "ada"

# `$partial: true` makes a node a partial: the function gets `rate` now, `price` later.
half_price = instantiate(config.half_price)
assert half_price(price=10.0) == 5.0

# `overrides` changes a copy; the loaded config stays untouched.
owned = instantiate(config.cart, Cart, overrides=["owner=grace"])
assert owned.owner == "grace"
assert "owner" not in config.cart

# An error from a constructor keeps its type and gets a note naming the node.
try:
    instantiate(config.cart, overrides={"items": [{"$class": "shop.Item"}]})
except TypeError as error:
    assert "while instantiating items.0 (shop.Item)" in error.__notes__
else:
    raise AssertionError("a missing constructor argument must fail")
