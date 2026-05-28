from __future__ import annotations


def long_trailing_stop(
    *,
    highest_price: float,
    atr: float,
    multiple: float = 2.0,
    current_stop: float | None = None,
) -> float:
    """Move a long trailing stop upward, never downward."""
    candidate = highest_price - atr * multiple
    if current_stop is None:
        return candidate
    return max(current_stop, candidate)


def short_trailing_stop(
    *,
    lowest_price: float,
    atr: float,
    multiple: float = 2.0,
    current_stop: float | None = None,
) -> float:
    """Move a short trailing stop downward, never upward."""
    candidate = lowest_price + atr * multiple
    if current_stop is None:
        return candidate
    return min(current_stop, candidate)
