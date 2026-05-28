from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import uuid

from nocares.domain import (
    AllocationPlan,
    CoinMetrics,
    EquitySnapshot,
    PaperOrder,
    PositionLegState,
    PositionState,
    TechnicalSnapshot,
)
from nocares.storage.repository import PortfolioRepository


class InMemoryPortfolioRepository(PortfolioRepository):
    def __init__(self) -> None:
        self.runs: dict[tuple[str, str], dict] = {}
        self.snapshots: list[TechnicalSnapshot] = []
        self.metrics: dict[str, CoinMetrics] = {}
        self.positions: dict[str, PositionState] = {}
        self.position_legs: list[PositionLegState] = []
        self.orders: dict[str, PaperOrder] = {}
        self.equity: list[EquitySnapshot] = []
        self.allocations: dict[str, float] = {}
        self.flags: dict[str, bool] = {"paper_trading_enabled": True}

    def fetch_latest_metrics(self) -> list[CoinMetrics]:
        return list(self.metrics.values())

    def save_allocation_plan(self, plan: AllocationPlan) -> None:
        self.allocations = {item.ticker: item.stack_size for item in plan.assigned_stacks}

    def create_or_get_run(self, run_type: str, bucket_ts: datetime) -> tuple[bool, str]:
        key = (run_type, bucket_ts.isoformat())
        existing = self.runs.get(key)
        if existing:
            return False, existing["run_id"]
        run_id = str(uuid.uuid4())
        self.runs[key] = {
            "run_id": run_id,
            "status": "running",
            "started_at": datetime.now(timezone.utc),
            "message": None,
        }
        return True, run_id

    def complete_run(self, run_id: str, status: str, message: str | None = None) -> None:
        for key, row in self.runs.items():
            if row["run_id"] == run_id:
                self.runs[key] = {
                    **row,
                    "status": status,
                    "message": message,
                    "ended_at": datetime.now(timezone.utc),
                }
                return

    def save_market_snapshots(self, rows: list[TechnicalSnapshot]) -> None:
        self.snapshots.extend(rows)

    def save_bot_metrics(self, rows: list[CoinMetrics]) -> None:
        for item in rows:
            self.metrics[item.ticker] = item

    def fetch_open_positions(self) -> list[PositionState]:
        return [item for item in self.positions.values() if item.status == "open"]

    def save_positions(self, rows: list[PositionState]) -> None:
        for row in rows:
            self.positions[row.ticker] = row

    def save_position_legs(self, rows: list[PositionLegState]) -> None:
        self.position_legs.extend(rows)

    def save_paper_orders(self, rows: list[PaperOrder]) -> None:
        for row in rows:
            self.orders.setdefault(row.dedupe_key, row)

    def save_equity_snapshot(self, row: EquitySnapshot) -> None:
        self.equity.append(row)

    def fetch_latest_allocation(self) -> dict[str, float]:
        return dict(self.allocations)

    def fetch_runtime_flag(self, flag_name: str, default: bool) -> bool:
        return self.flags.get(flag_name, default)


def clone_position_as_closed(position: PositionState, realized_pnl_pct: float, close_ts: datetime) -> PositionState:
    return replace(
        position,
        status="closed",
        closed_at=close_ts,
        realized_pnl_pct=realized_pnl_pct,
    )
