from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nocares.allocation.rules import build_allocation_plan, validate_allocation_plan
from nocares.domain import CoinMetrics, PositionStatus, Regime


class AllocationRulesTest(unittest.TestCase):
    def test_plan_respects_core_portfolio_limits(self) -> None:
        metrics = [
            CoinMetrics("SOL", 34, 1.8, 42, 0.35, Regime.TREND_UP, score=60),
            CoinMetrics("BTC", 29, 1.2, 20, 0.18, Regime.TREND_UP, score=45),
            CoinMetrics("DOT", 31, 1.6, 35, 0.22, Regime.TREND_UP, score=48),
            CoinMetrics("NEAR", 24, 1.4, 18, 0.10, Regime.TRANSITION, score=26),
            CoinMetrics("AVAX", 27, 1.5, 30, 0.15, Regime.TREND_UP, score=30),
        ]

        plan = build_allocation_plan(metrics)
        validate_allocation_plan(plan)

        self.assertEqual(len(plan.assigned_stacks), 4)
        self.assertGreaterEqual(plan.reserve_wallet, 20)
        self.assertLessEqual(plan.allocated_stack, 80)
        for item in plan.assigned_stacks:
            self.assertGreaterEqual(item.stack_size, 5)
            self.assertLessEqual(item.stack_size, 30)

    def test_stale_non_selected_position_is_closed(self) -> None:
        metrics = [
            CoinMetrics("SOL", 34, 1.8, 42, 0.35, Regime.TREND_UP, score=60),
            CoinMetrics("BTC", 29, 1.2, 20, 0.18, Regime.TREND_UP, score=45),
            CoinMetrics("DOT", 31, 1.6, 35, 0.22, Regime.TREND_UP, score=48),
            CoinMetrics("NEAR", 24, 1.4, 18, 0.10, Regime.TRANSITION, score=26),
            CoinMetrics(
                "ETH",
                13,
                0.9,
                -5,
                -0.05,
                Regime.RANGE,
                PositionStatus.TRANCHE_1,
                5.0,
                -0.2,
                12,
            ),
        ]

        plan = build_allocation_plan(metrics)

        self.assertIn("ETH", {command.ticker for command in plan.close_positions})


if __name__ == "__main__":
    unittest.main()
