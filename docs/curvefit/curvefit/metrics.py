def mse(predictions: list[float], targets: list[float]) -> float:
    """The mean squared error."""
    pairs = zip(predictions, targets, strict=True)
    return sum((p - t) ** 2 for p, t in pairs) / len(targets)


def mae(predictions: list[float], targets: list[float]) -> float:
    """The mean absolute error."""
    pairs = zip(predictions, targets, strict=True)
    return sum(abs(p - t) for p, t in pairs) / len(targets)
