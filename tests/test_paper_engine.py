from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nocares.domain import PositionState, Regime, TechnicalSnapshot
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


class PaperEngineTest(unittest.TestCase):
    def test_tranche_one_entry(self) -> None:
        now = datetime.now(timezone.utc)
        snapshot = TechnicalSnapshot(
            ticker="BTC/USDT",
            timeframe="5m",
            ts=now,
            price=100.0,
            volume=1200,
            ema_fast=101,
            ema_slow=99,
            atr=2.0,
            adx=30,
            momentum=0.03,
            volume_ratio=1.2,
            regime=Regime.TREND_UP,
            score=42,
        )
        result = execute_paper_cycle(
            run_id="run-1",
            run_ts=now,
            snapshots={"BTC/USDT": snapshot},
            allocations={"BTC/USDT": 20.0},
            open_positions=[],
            config=_config(),
        )
        self.assertEqual(len(result.orders), 1)
        self.assertEqual(result.orders[0].side, "buy")
        open_positions = [x for x in result.positions if x.status == "open"]
        self.assertEqual(len(open_positions), 1)
        self.assertEqual(open_positions[0].tranche_status, "tranche_1")

    def test_trailing_stop_never_decreases(self) -> None:
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
            highest_price=100.0,
            opened_at=now - timedelta(hours=1),
        )
        snapshot = TechnicalSnapshot(
            ticker="BTC/USDT",
            timeframe="5m",
            ts=now,
            price=110.0,
            volume=1000,
            ema_fast=105,
            ema_slow=100,
            atr=2.0,
            adx=30,
            momentum=0.05,
            volume_ratio=1.1,
            regime=Regime.TREND_UP,
            score=40,
        )
        result = execute_paper_cycle(
            run_id="run-2",
            run_ts=now,
            snapshots={"BTC/USDT": snapshot},
            allocations={},
            open_positions=[open_position],
            config=_config(),
        )
        updated = [x for x in result.positions if x.status == "open"][0]
        self.assertGreaterEqual(updated.stop_price, 95.0)

    def test_stop_hit_closes_position(self) -> None:
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
            stop_price=98.0,
            highest_price=100.0,
            opened_at=now - timedelta(hours=1),
        )
        snapshot = TechnicalSnapshot(
            ticker="BTC/USDT",
            timeframe="5m",
            ts=now,
            price=90.0,
            volume=1000,
            ema_fast=95,
            ema_slow=100,
            atr=2.0,
            adx=18,
            momentum=-0.04,
            volume_ratio=0.9,
            regime=Regime.RANGE,
            score=-10,
        )
        result = execute_paper_cycle(
            run_id="run-3",
            run_ts=now,
            snapshots={"BTC/USDT": snapshot},
            allocations={},
            open_positions=[open_position],
            config=_config(),
        )
        closed_positions = [x for x in result.positions if x.status == "closed"]
        self.assertEqual(len(closed_positions), 1)
        self.assertEqual(result.orders[0].side, "sell")


if __name__ == "__main__":
    unittest.main()
