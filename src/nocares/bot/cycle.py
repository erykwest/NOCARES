from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from typing import Any

from nocares.allocation.rules import build_allocation_plan, validate_allocation_plan
from nocares.config import load_config
from nocares.domain import CoinMetrics
from nocares.market import BinanceMarketClient, build_coin_metrics, build_technical_snapshot
from nocares.risk import PaperEngineConfig, execute_paper_cycle
from nocares.storage import InMemoryPortfolioRepository, SupabasePortfolioRepository


def main() -> None:
    parser = argparse.ArgumentParser(description="NOCARES 5m paper cycle")
    parser.add_argument("--mode", default="paper", choices=["paper"])
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--mock", action="store_true")
    args = parser.parse_args()

    config = load_config()
    runtime_cfg = config.get("runtime", {})
    effective_dry_run = bool(args.dry_run or runtime_cfg.get("default_dry_run", False))
    repo = _build_repository(dry_run=effective_dry_run)

    now = datetime.now(timezone.utc)
    bucket_ts = floor_time(now, 5)
    created, run_id = repo.create_or_get_run("paper_cycle", bucket_ts)
    if not created:
        print(json.dumps({"status": "skipped", "reason": "run bucket already processed", "run_id": run_id}))
        return

    try:
        if not repo.fetch_runtime_flag("paper_trading_enabled", True):
            repo.complete_run(run_id, "skipped", "paper trading disabled by runtime flag")
            print(json.dumps({"status": "skipped", "run_id": run_id, "reason": "runtime flag off"}))
            return

        market_cfg = config["market"]
        strategy_cfg = config["strategy"]
        client = BinanceMarketClient(
            base_url=market_cfg.get("binance_base_url", "https://api.binance.com"),
            timeout_seconds=int(market_cfg.get("request_timeout_seconds", 10)),
            max_retries=int(market_cfg.get("max_retries", 3)),
            request_pause_ms=int(market_cfg.get("request_pause_ms", 100)),
            use_mock=bool(args.mock),
        )

        snapshots = []
        metrics: list[CoinMetrics] = []
        for pair in market_cfg["tracked_pairs"]:
            candles = client.fetch_klines(pair, market_cfg["primary_timeframe"], limit=120)
            if len(candles) < 20:
                continue
            closes = [item.close_price for item in candles]
            highs = [item.high_price for item in candles]
            lows = [item.low_price for item in candles]
            volumes = [item.volume for item in candles]
            snapshot = build_technical_snapshot(
                pair=pair,
                timeframe=market_cfg["primary_timeframe"],
                closes=closes,
                highs=highs,
                lows=lows,
                volumes=volumes,
                ts=candles[-1].close_time,
                adx_range_threshold=float(strategy_cfg["adx_range_threshold"]),
                adx_trend_threshold=float(strategy_cfg["adx_trend_threshold"]),
                momentum_lookback=int(strategy_cfg.get("momentum_lookback", 3)),
                volume_ratio_window=int(strategy_cfg.get("volume_ratio_window", 10)),
            )
            snapshots.append(snapshot)
            metrics.append(build_coin_metrics(snapshot))

        repo.save_market_snapshots(snapshots)
        repo.save_bot_metrics(metrics)

        allocations = repo.fetch_latest_allocation()
        if not allocations:
            plan = build_allocation_plan(
                metrics,
                total_stack=float(config["portfolio"]["base_stack"]),
                reserve_pct=float(config["portfolio"]["reserve_pct"]),
                active_coin_slots=int(config["portfolio"]["active_coin_slots"]),
                min_coin_pct=float(config["portfolio"]["min_coin_pct"]),
                max_coin_pct=float(config["portfolio"]["max_coin_pct"]),
                emergency_min_pct=float(config["portfolio"]["emergency_min_pct"]),
                emergency_max_pct=float(config["portfolio"]["emergency_max_pct"]),
                max_stale_position_hours=float(config["portfolio"]["max_stale_position_hours"]),
            )
            validate_allocation_plan(
                plan,
                reserve_pct=float(config["portfolio"]["reserve_pct"]),
                min_coin_pct=float(config["portfolio"]["min_coin_pct"]),
                max_coin_pct=float(config["portfolio"]["max_coin_pct"]),
                active_coin_slots=int(config["portfolio"]["active_coin_slots"]),
            )
            repo.save_allocation_plan(plan)
            allocations = {item.ticker: item.stack_size for item in plan.assigned_stacks}

        open_positions = repo.fetch_open_positions()
        snap_map = {item.ticker: item for item in snapshots}
        engine_cfg = PaperEngineConfig(
            total_stack=float(config["portfolio"]["base_stack"]),
            tranches=tuple(float(x) for x in strategy_cfg["tranches"]),
            initial_stop_atr_multiple=float(strategy_cfg["initial_stop_atr_multiple"]),
            trail_stop_atr_multiple=float(strategy_cfg["trail_stop_atr_multiple"]),
            min_tranche2_move_atr=float(strategy_cfg.get("min_tranche2_move_atr", 1.0)),
            min_tranche3_move_atr=float(strategy_cfg.get("min_tranche3_move_atr", 2.0)),
            max_portfolio_exposure_pct=float(config["risk"]["max_portfolio_exposure_pct"]),
            max_stale_position_hours=float(config["portfolio"]["max_stale_position_hours"]),
        )
        result = execute_paper_cycle(
            run_id=run_id,
            run_ts=now,
            snapshots=snap_map,
            allocations=allocations,
            open_positions=open_positions,
            config=engine_cfg,
        )

        repo.save_position_legs(result.legs)
        repo.save_paper_orders(result.orders)
        repo.save_positions(result.positions)
        repo.save_equity_snapshot(result.equity)
        repo.complete_run(run_id, "success", f"snapshots={len(snapshots)} orders={len(result.orders)}")

        print(
            json.dumps(
                {
                    "status": "success",
                    "run_id": run_id,
                    "snapshot_count": len(snapshots),
                    "orders_count": len(result.orders),
                    "open_positions": len([x for x in result.positions if x.status == "open"]),
                    "equity": result.equity.equity,
                    "dry_run": effective_dry_run,
                    "mock": bool(args.mock),
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


def floor_time(ts: datetime, minutes: int) -> datetime:
    minute = (ts.minute // minutes) * minutes
    return ts.replace(minute=minute, second=0, microsecond=0)


if __name__ == "__main__":
    main()
