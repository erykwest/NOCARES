from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os

from nocares.allocation.rules import build_allocation_plan, validate_allocation_plan
from nocares.config import load_config
from nocares.domain import CoinMetrics, Regime
from nocares.llm.rebalance import allocation_plan_from_payload, request_llm_allocation
from nocares.storage import InMemoryPortfolioRepository, SupabasePortfolioRepository


def main() -> None:
    parser = argparse.ArgumentParser(description="NOCARES hourly portfolio rebalance")
    parser.add_argument("--mode", default="deterministic", choices=["deterministic", "llm"])
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--mock", action="store_true")
    args = parser.parse_args()

    config = load_config()
    runtime_cfg = config.get("runtime", {})
    dry_run = bool(args.dry_run or runtime_cfg.get("default_dry_run", False))
    repo = _build_repository(dry_run=dry_run)

    bucket_ts = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    created, run_id = repo.create_or_get_run("rebalance_hourly", bucket_ts)
    if not created:
        print(json.dumps({"status": "skipped", "run_id": run_id, "reason": "rebalance already done"}))
        return

    try:
        metrics = repo.fetch_latest_metrics()
        if not metrics and args.mock:
            metrics = _mock_metrics()
        if not metrics:
            repo.complete_run(run_id, "skipped", "no metrics available")
            print(json.dumps({"status": "skipped", "run_id": run_id, "reason": "no metrics"}))
            return

        portfolio_cfg = config["portfolio"]
        total_stack = float(portfolio_cfg["base_stack"])
        reserve_pct = float(portfolio_cfg["reserve_pct"])
        plan = None

        if args.mode == "llm" and os.getenv("OPENAI_API_KEY"):
            try:
                payload = request_llm_allocation(
                    metrics=metrics,
                    total_stack=total_stack,
                    reserve_pct=reserve_pct,
                    model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
                    api_key=os.getenv("OPENAI_API_KEY", ""),
                )
                plan = allocation_plan_from_payload(payload, total_stack=total_stack)
            except Exception:
                plan = None

        if plan is None:
            plan = build_allocation_plan(
                metrics,
                total_stack=total_stack,
                reserve_pct=reserve_pct,
                active_coin_slots=int(portfolio_cfg["active_coin_slots"]),
                min_coin_pct=float(portfolio_cfg["min_coin_pct"]),
                max_coin_pct=float(portfolio_cfg["max_coin_pct"]),
                emergency_min_pct=float(portfolio_cfg["emergency_min_pct"]),
                emergency_max_pct=float(portfolio_cfg["emergency_max_pct"]),
                max_stale_position_hours=float(portfolio_cfg["max_stale_position_hours"]),
            )

        validate_allocation_plan(
            plan,
            reserve_pct=reserve_pct,
            min_coin_pct=float(portfolio_cfg["min_coin_pct"]),
            max_coin_pct=float(portfolio_cfg["max_coin_pct"]),
            active_coin_slots=int(portfolio_cfg["active_coin_slots"]),
        )
        repo.save_allocation_plan(plan)
        repo.complete_run(run_id, "success", f"assigned={len(plan.assigned_stacks)}")

        print(
            json.dumps(
                {
                    "status": "success",
                    "run_id": run_id,
                    "assigned": len(plan.assigned_stacks),
                    "reserve_wallet": plan.reserve_wallet,
                    "mode": args.mode,
                    "dry_run": dry_run,
                }
            )
        )
    except Exception as exc:  # pragma: no cover - surfaced to logs
        repo.complete_run(run_id, "failed", str(exc))
        raise


def _build_repository(dry_run: bool):
    if dry_run:
        return InMemoryPortfolioRepository()

    try:
        return SupabasePortfolioRepository(
            url=os.getenv("SUPABASE_URL"),
            service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
        )
    except Exception:
        return InMemoryPortfolioRepository()


def _mock_metrics() -> list[CoinMetrics]:
    return [
        CoinMetrics("BTC/USDT", adx=31, atr=1.8, volume_delta=0.24, current_regime=Regime.TREND_UP, score=44),
        CoinMetrics("ETH/USDT", adx=28, atr=1.6, volume_delta=0.19, current_regime=Regime.TREND_UP, score=38),
        CoinMetrics("SOL/USDT", adx=35, atr=2.2, volume_delta=0.33, current_regime=Regime.TREND_UP, score=52),
        CoinMetrics("AVAX/USDT", adx=26, atr=2.1, volume_delta=0.17, current_regime=Regime.TREND_UP, score=31),
        CoinMetrics("ADA/USDT", adx=16, atr=1.2, volume_delta=-0.03, current_regime=Regime.RANGE, score=10),
    ]


if __name__ == "__main__":
    main()
