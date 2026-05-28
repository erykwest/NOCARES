from __future__ import annotations

from datetime import datetime
from typing import Protocol

from nocares.domain import (
    AllocationPlan,
    BotRun,
    CoinMetrics,
    EquitySnapshot,
    PaperOrder,
    PositionLegState,
    PositionState,
    TechnicalSnapshot,
)


class PortfolioRepository(Protocol):
    """Storage boundary used by bots and the LLM layer."""

    def fetch_latest_metrics(self) -> list[CoinMetrics]:
        """Return compact metrics for all tracked tickers."""

    def save_allocation_plan(self, plan: AllocationPlan) -> None:
        """Persist a validated allocation plan."""

    def create_or_get_run(self, run_type: str, bucket_ts: datetime) -> tuple[bool, str]:
        """Create a run row if absent. Returns (created, run_id)."""

    def complete_run(self, run_id: str, status: str, message: str | None = None) -> None:
        """Mark a run as completed or failed."""

    def save_market_snapshots(self, rows: list[TechnicalSnapshot]) -> None:
        """Persist technical snapshots."""

    def save_bot_metrics(self, rows: list[CoinMetrics]) -> None:
        """Persist compact per-symbol metrics."""

    def fetch_open_positions(self) -> list[PositionState]:
        """Return current open positions."""

    def save_positions(self, rows: list[PositionState]) -> None:
        """Persist current positions state."""

    def save_position_legs(self, rows: list[PositionLegState]) -> None:
        """Persist new legs for pyramiding."""

    def save_paper_orders(self, rows: list[PaperOrder]) -> None:
        """Persist simulated orders."""

    def save_equity_snapshot(self, row: EquitySnapshot) -> None:
        """Persist one equity snapshot for the run."""

    def fetch_latest_allocation(self) -> dict[str, float]:
        """Return latest assigned stack by ticker."""

    def fetch_runtime_flag(self, flag_name: str, default: bool) -> bool:
        """Return runtime boolean flag or default if missing."""
