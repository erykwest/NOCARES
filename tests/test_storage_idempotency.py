from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nocares.domain import PaperOrder
from nocares.storage.in_memory import InMemoryPortfolioRepository


class StorageIdempotencyTest(unittest.TestCase):
    def test_run_bucket_is_unique(self) -> None:
        repo = InMemoryPortfolioRepository()
        ts = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        created_a, run_a = repo.create_or_get_run("paper_cycle", ts)
        created_b, run_b = repo.create_or_get_run("paper_cycle", ts)
        self.assertTrue(created_a)
        self.assertFalse(created_b)
        self.assertEqual(run_a, run_b)

    def test_order_dedupe_key_prevents_duplicates(self) -> None:
        repo = InMemoryPortfolioRepository()
        now = datetime.now(timezone.utc)
        order = PaperOrder(
            run_id="run-1",
            dedupe_key="run-1:BTC/USDT:buy:1",
            ticker="BTC/USDT",
            side="buy",
            notional=10,
            quantity=0.1,
            price=100,
            reason="entry",
            created_at=now,
        )
        repo.save_paper_orders([order, order])
        self.assertEqual(len(repo.orders), 1)


if __name__ == "__main__":
    unittest.main()
