from collections.abc import Callable


def tax_free(price: float) -> float:
    return price


def discounted(price: float, rate: float) -> float:
    return price * (1 - rate)


class Item:
    def __init__(self, name: str, price: float) -> None:
        self.name = name
        self.price = price


class Cart:
    def __init__(
        self, items: list[Item], pricing: Callable[[float], float], owner: str = ""
    ) -> None:
        self.items = items
        self.pricing = pricing
        self.owner = owner

    def total(self) -> float:
        return sum(self.pricing(item.price) for item in self.items)
