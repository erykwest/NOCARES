from __future__ import annotations

from dataclasses import dataclass


DEFAULT_TRANCHES = (0.50, 0.30, 0.20)


@dataclass(frozen=True)
class PositionLeg:
    size: float
    entry_price: float


def tranche_size(assigned_stack: float, tranche_index: int) -> float:
    """Return the absolute stack size for a 50-30-20 tranche."""
    return assigned_stack * DEFAULT_TRANCHES[tranche_index]


def average_entry_price(legs: list[PositionLeg] | tuple[PositionLeg, ...]) -> float:
    """Calculate weighted average entry price for pyramid legs."""
    total_size = sum(leg.size for leg in legs)
    if total_size <= 0:
        raise ValueError("total position size must be positive")
    return sum(leg.size * leg.entry_price for leg in legs) / total_size
