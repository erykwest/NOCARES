from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nocares.bot.cycle import _apply_allocation_overrides
from nocares.domain import PairOverride, PositionState, Regime, TechnicalSnapshot
from nocares.risk.paper_engine import PaperEngineConfig, execute_paper_cycle


def _config() -> PaperEngineConfig:
    return PaperEngineConfig(
        total_stack=100.0,
        tranches=(0.5, 0.3, 0.2),
        initial_stop_atr_multiple=2.0,
        trail_stop_atr_multiple=2.0,
        min_tranche2_move_atr=1.0,
        min_tranche3_move_atr=2.0,
        max_portfolio_exposure_pct=80.0,
        max_stale_position_hours=4.0,
    )


class OverrideTests(unittest.TestCase):
    def test_allocation_override_can_block_new_entries(self) -> None:
        override = PairOverride(ticker="BTC/USDT", enabled=True, block_new_entries=True, assigned_stack_override=30)
        out = _apply_allocation_overrides(
            allocations={"BTC/USDT": 20.0, "ETH/USDT": 10.0},
            open_positions=[],
            overrides={"BTC/USDT": override},
        )
        self.assertNotIn("BTC/USDT", out)
        self.assertEqual(out["ETH/USDT"], 10.0)

    def test_force_close_override_closes_open_position(self) -> None:
        now = datetime.now(timezone.utc)
        open_position = PositionState(
            ticker="BTC/USDT",
            side="long",
            status="open",
            assigned_stack=20.0,
            tranche_status="tranche_1",
            average_entry_price=100.0,
            quantity=1.0,
            invested_notional=100.0,
            stop_price=95.0,
            highest_price=102.0,
            opened_at=now - timedelta(hours=1),
        )
        snapshot = TechnicalSnapshot(
            ticker="BTC/USDT",
            timeframe="5m",
            ts=now,
            price=101.0,
            volume=1000,
            ema_fast=102.0,
            ema_slow=99.0,
            atr=2.0,
            adx=30.0,
            momentum=0.02,
            volume_ratio=1.1,
            regime=Regime.TREND_UP,
            score=20.0,
        )
        override = PairOverride(ticker="BTC/USDT", enabled=True, force_close=True)
        result = execute_paper_cycle(
            run_id="run-override",
            run_ts=now,
            snapshots={"BTC/USDT": snapshot},
            allocations={},
            open_positions=[open_position],
            config=_config(),
            pair_overrides={"BTC/USDT": override},
        )
        self.assertEqual(result.orders[0].side, "sell")
        self.assertEqual(result.orders[0].reason, "override_force_close")


if __name__ == "__main__":
    unittest.main()
