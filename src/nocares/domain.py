from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
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


@dataclass(frozen=True)
class Candle:
    symbol: str
    open_time: datetime
    close_time: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float


@dataclass(frozen=True)
class TechnicalSnapshot:
    ticker: str
    timeframe: str
    ts: datetime
    price: float
    volume: float
    ema_fast: float | None
    ema_slow: float | None
    atr: float | None
    adx: float | None
    momentum: float | None
    volume_ratio: float | None
    regime: Regime
    score: float


@dataclass(frozen=True)
class BotRun:
    run_id: str
    run_type: str
    bucket_ts: datetime
    status: str
    message: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None


@dataclass(frozen=True)
class PaperOrder:
    run_id: str
    dedupe_key: str
    ticker: str
    side: str
    notional: float
    quantity: float
    price: float
    reason: str
    created_at: datetime


@dataclass(frozen=True)
class PositionState:
    ticker: str
    side: str
    status: str
    assigned_stack: float
    tranche_status: str
    average_entry_price: float
    quantity: float
    invested_notional: float
    stop_price: float
    highest_price: float
    opened_at: datetime
    closed_at: datetime | None = None
    realized_pnl_pct: float | None = None


@dataclass(frozen=True)
class PositionLegState:
    ticker: str
    run_id: str
    tranche_index: int
    notional: float
    quantity: float
    entry_price: float
    created_at: datetime


@dataclass(frozen=True)
class EquitySnapshot:
    run_id: str
    ts: datetime
    cash_balance: float
    exposure: float
    equity: float


@dataclass(frozen=True)
class PairOverride:
    ticker: str
    enabled: bool = False
    block_new_entries: bool = False
    force_close: bool = False
    assigned_stack_override: float | None = None
    tranche1_pct: float | None = None
    tranche2_pct: float | None = None
    tranche3_pct: float | None = None
    initial_stop_atr_multiple: float | None = None
    trail_stop_atr_multiple: float | None = None
    max_stale_position_hours: float | None = None
    notes: str | None = None
