from __future__ import annotations

import json

from nocares.allocation.rules import build_allocation_plan, validate_allocation_plan
from nocares.domain import CoinMetrics, PositionStatus, Regime


def main() -> None:
    metrics = [
        CoinMetrics("SOL", 34, 1.8, 42, 0.35, Regime.TREND_UP, score=60),
        CoinMetrics("BTC", 29, 1.2, 20, 0.18, Regime.TREND_UP, PositionStatus.TRANCHE_1, 1.5, 1.2, 45),
        CoinMetrics("DOT", 31, 1.6, 35, 0.22, Regime.TREND_UP, score=48),
        CoinMetrics("NEAR", 24, 1.4, 18, 0.10, Regime.TRANSITION, score=26),
        CoinMetrics("ETH", 13, 0.9, -5, -0.05, Regime.RANGE, PositionStatus.TRANCHE_1, 5.0, -0.2, 12),
        CoinMetrics("AVAX", 27, 1.5, 30, 0.15, Regime.TREND_UP, score=30),
    ]
    plan = build_allocation_plan(metrics)
    validate_allocation_plan(plan)
    print(json.dumps(plan.as_dict(), indent=2))


if __name__ == "__main__":
    main()
