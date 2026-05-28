from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nocares.domain import Regime
from nocares.market.indicators import build_technical_snapshot


class MarketIndicatorsTest(unittest.TestCase):
    def test_trend_snapshot_classifies_trend_up(self) -> None:
        closes = [100 + (i * 0.6) for i in range(70)]
        highs = [value * 1.002 for value in closes]
        lows = [value * 0.998 for value in closes]
        volumes = [1000 + (i * 3) for i in range(70)]

        snapshot = build_technical_snapshot(
            pair="BTC/USDT",
            timeframe="5m",
            closes=closes,
            highs=highs,
            lows=lows,
            volumes=volumes,
            ts=datetime.now(timezone.utc),
            adx_range_threshold=20,
            adx_trend_threshold=25,
        )

        self.assertEqual(snapshot.regime, Regime.TREND_UP)
        self.assertIsNotNone(snapshot.adx)
        self.assertGreater(snapshot.score, 0)

    def test_range_snapshot_classifies_range(self) -> None:
        closes = [100 + (0.02 if i % 2 else -0.02) for i in range(70)]
        highs = [value + 0.05 for value in closes]
        lows = [value - 0.05 for value in closes]
        volumes = [1000 for _ in range(70)]

        snapshot = build_technical_snapshot(
            pair="ETH/USDT",
            timeframe="5m",
            closes=closes,
            highs=highs,
            lows=lows,
            volumes=volumes,
            ts=datetime.now(timezone.utc),
            adx_range_threshold=20,
            adx_trend_threshold=25,
        )

        self.assertEqual(snapshot.regime, Regime.RANGE)

    def test_insufficient_data_does_not_crash(self) -> None:
        closes = [100 + i for i in range(8)]
        highs = [value + 0.1 for value in closes]
        lows = [value - 0.1 for value in closes]
        volumes = [100 for _ in closes]

        snapshot = build_technical_snapshot(
            pair="SOL/USDT",
            timeframe="5m",
            closes=closes,
            highs=highs,
            lows=lows,
            volumes=volumes,
            ts=datetime.now(timezone.utc),
            adx_range_threshold=20,
            adx_trend_threshold=25,
        )

        self.assertEqual(snapshot.regime, Regime.TRANSITION)
        self.assertIsNone(snapshot.adx)
        self.assertEqual(snapshot.score, 0.0)


if __name__ == "__main__":
    unittest.main()
