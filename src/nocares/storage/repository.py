from __future__ import annotations

from typing import Protocol

from nocares.domain import AllocationPlan, CoinMetrics


class PortfolioRepository(Protocol):
    """Storage boundary used by bots and the LLM layer."""

    def fetch_latest_metrics(self) -> list[CoinMetrics]:
        """Return compact metrics for all tracked tickers."""

    def save_allocation_plan(self, plan: AllocationPlan) -> None:
        """Persist a validated allocation plan."""
