from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class Regime(str, Enum):
    TREND_UP = "trend_up"
    TREND_DOWN = "trend_down"
    RANGE = "range"
    TRANSITION = "transition"


class PositionStatus(str, Enum):
    FLAT = "flat"
    TRANCHE_1 = "tranche_1"
    TRANCHE_2 = "tranche_2"
    TRANCHE_3 = "tranche_3"


def enum_value(value: Any) -> str:
    if isinstance(value, Enum):
        return value.value
    return str(value)


@dataclass(frozen=True)
class CoinMetrics:
    ticker: str
    adx: float
    atr: float
    volume_delta: float
    book_imbalance: float = 0.0
    current_regime: Regime | str = Regime.RANGE
    position_status: PositionStatus | str = PositionStatus.FLAT
    position_duration_hours: float = 0.0
    unrealized_pnl_pct: float = 0.0
    score: float | None = None
    correlation_group: str | None = None

    @property
    def is_flat(self) -> bool:
        return enum_value(self.position_status) == PositionStatus.FLAT.value


@dataclass(frozen=True)
class AssignedStack:
    ticker: str
    stack_size: float
    status: str
    reason: str


@dataclass(frozen=True)
class CloseCommand:
    ticker: str
    reason: str


@dataclass(frozen=True)
class EmergencyReserveTarget:
    ticker: str
    max_draw_from_reserve: float
    trigger_condition: str


@dataclass(frozen=True)
class AllocationPlan:
    total_stack: float
    reserve_wallet: float
    assigned_stacks: tuple[AssignedStack, ...]
    close_positions: tuple[CloseCommand, ...] = ()
    emergency_reserve_targets: tuple[EmergencyReserveTarget, ...] = ()

    @property
    def allocated_stack(self) -> float:
        return sum(item.stack_size for item in self.assigned_stacks)

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_stack": self.total_stack,
            "reserve_wallet": self.reserve_wallet,
            "allocated_stack": self.allocated_stack,
            "assigned_stacks": [_clean_enums(asdict(item)) for item in self.assigned_stacks],
            "commands": {
                "close_positions": [_clean_enums(asdict(item)) for item in self.close_positions],
                "emergency_reserve_targets": [
                    _clean_enums(asdict(item)) for item in self.emergency_reserve_targets
                ],
            },
        }


def _clean_enums(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _clean_enums(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_clean_enums(item) for item in value]
    return value
