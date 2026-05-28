from __future__ import annotations

from datetime import datetime, timezone
import os
import uuid

from nocares.domain import (
    AllocationPlan,
    CoinMetrics,
    EquitySnapshot,
    PaperOrder,
    PairOverride,
    PositionLegState,
    PositionState,
    TechnicalSnapshot,
    enum_value,
)
from nocares.storage.repository import PortfolioRepository


class SupabasePortfolioRepository(PortfolioRepository):
    """Concrete storage adapter backed by Supabase Data API."""

    def __init__(self, url: str | None = None, service_role_key: str | None = None) -> None:
        try:
            from supabase import create_client
        except ImportError as exc:
            raise RuntimeError("supabase dependency is required for SupabasePortfolioRepository") from exc

        self.url = url or os.getenv("SUPABASE_URL")
        self.key = service_role_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not self.url or not self.key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")
        self.client = create_client(self.url, self.key)

    def fetch_latest_metrics(self) -> list[CoinMetrics]:
        response = self.client.table("bot_metrics").select("*").execute()
        data = response.data or []
        return [
            CoinMetrics(
                ticker=row["ticker"],
                adx=float(row.get("adx", 0)),
                atr=float(row.get("atr", 0)),
                volume_delta=float(row.get("volume_delta", 0)),
                book_imbalance=float(row.get("book_imbalance", 0)),
                current_regime=row.get("current_regime", "range"),
                position_status=row.get("position_status", "flat"),
                position_duration_hours=float(row.get("position_duration_hours", 0)),
                unrealized_pnl_pct=float(row.get("unrealized_pnl_pct", 0)),
                score=float(row["score"]) if row.get("score") is not None else None,
                correlation_group=row.get("correlation_group"),
            )
            for row in data
        ]

    def save_allocation_plan(self, plan: AllocationPlan) -> None:
        rows = [
            {
                "ticker": item.ticker,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "assigned_stack": item.stack_size,
                "is_active": True,
                "emergency_reserve_allowed": 0,
                "status": item.status,
                "reason": item.reason,
            }
            for item in plan.assigned_stacks
        ]
        if rows:
            self.client.table("portfolio_allocation").upsert(rows, on_conflict="ticker").execute()
        self.client.table("portfolio_decisions").insert(
            {
                "decided_at": datetime.now(timezone.utc).isoformat(),
                "total_stack": plan.total_stack,
                "reserve_wallet": plan.reserve_wallet,
                "payload": plan.as_dict(),
                "source": "deterministic",
            }
        ).execute()

    def create_or_get_run(self, run_type: str, bucket_ts: datetime) -> tuple[bool, str]:
        bucket = bucket_ts.isoformat()
        lookup = (
            self.client.table("bot_runs")
            .select("run_id")
            .eq("run_type", run_type)
            .eq("bucket_ts", bucket)
            .limit(1)
            .execute()
        )
        if lookup.data:
            return False, lookup.data[0]["run_id"]

        run_id = str(uuid.uuid4())
        self.client.table("bot_runs").insert(
            {
                "run_id": run_id,
                "run_type": run_type,
                "bucket_ts": bucket,
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
            }
        ).execute()
        return True, run_id

    def complete_run(self, run_id: str, status: str, message: str | None = None) -> None:
        self.client.table("bot_runs").update(
            {
                "status": status,
                "message": message,
                "ended_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("run_id", run_id).execute()

    def save_market_snapshots(self, rows: list[TechnicalSnapshot]) -> None:
        if not rows:
            return
        payload = [
            {
                "ticker": row.ticker,
                "timeframe": row.timeframe,
                "ts": row.ts.isoformat(),
                "price": row.price,
                "volume": row.volume,
                "adx": row.adx,
                "atr": row.atr,
                "current_regime": row.regime.value,
                "score": row.score,
                "ema_fast": row.ema_fast,
                "ema_slow": row.ema_slow,
                "momentum": row.momentum,
                "volume_ratio": row.volume_ratio,
            }
            for row in rows
        ]
        self.client.table("technical_snapshots").insert(payload).execute()

    def save_bot_metrics(self, rows: list[CoinMetrics]) -> None:
        if not rows:
            return
        payload = [
            {
                "ticker": row.ticker,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "adx": row.adx,
                "atr": row.atr,
                "volume_delta": row.volume_delta,
                "book_imbalance": row.book_imbalance,
                "current_regime": enum_value(row.current_regime),
                "position_status": enum_value(row.position_status),
                "position_duration_hours": row.position_duration_hours,
                "unrealized_pnl_pct": row.unrealized_pnl_pct,
                "score": row.score,
                "correlation_group": row.correlation_group,
            }
            for row in rows
        ]
        self.client.table("bot_metrics").upsert(payload, on_conflict="ticker").execute()

    def fetch_open_positions(self) -> list[PositionState]:
        rows = self.client.table("positions").select("*").eq("status", "open").execute().data or []
        result = []
        for row in rows:
            result.append(
                PositionState(
                    ticker=row["ticker"],
                    side=row.get("side", "long"),
                    status=row.get("status", "open"),
                    assigned_stack=float(row.get("assigned_stack", 0)),
                    tranche_status=row.get("tranche_status", "tranche_1"),
                    average_entry_price=float(row.get("average_entry_price") or 0),
                    quantity=float(row.get("quantity") or 0),
                    invested_notional=float(row.get("invested_notional") or 0),
                    stop_price=float(row.get("stop_price") or 0),
                    highest_price=float(row.get("highest_price") or row.get("average_entry_price") or 0),
                    opened_at=_parse_ts(row.get("opened_at")),
                    closed_at=_parse_ts(row.get("closed_at")) if row.get("closed_at") else None,
                    realized_pnl_pct=float(row["realized_pnl_pct"]) if row.get("realized_pnl_pct") is not None else None,
                )
            )
        return result

    def save_positions(self, rows: list[PositionState]) -> None:
        if not rows:
            return
        payload = [
            {
                "ticker": row.ticker,
                "side": row.side,
                "status": row.status,
                "assigned_stack": row.assigned_stack,
                "tranche_status": row.tranche_status,
                "average_entry_price": row.average_entry_price,
                "quantity": row.quantity,
                "invested_notional": row.invested_notional,
                "stop_price": row.stop_price,
                "highest_price": row.highest_price,
                "opened_at": row.opened_at.isoformat(),
                "closed_at": row.closed_at.isoformat() if row.closed_at else None,
                "realized_pnl_pct": row.realized_pnl_pct,
            }
            for row in rows
        ]
        self.client.table("positions").upsert(payload, on_conflict="ticker").execute()

    def save_position_legs(self, rows: list[PositionLegState]) -> None:
        if not rows:
            return
        payload = [
            {
                "ticker": row.ticker,
                "run_id": row.run_id,
                "tranche_index": row.tranche_index,
                "notional": row.notional,
                "quantity": row.quantity,
                "entry_price": row.entry_price,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]
        self.client.table("position_legs").insert(payload).execute()

    def save_paper_orders(self, rows: list[PaperOrder]) -> None:
        if not rows:
            return
        payload = [
            {
                "run_id": row.run_id,
                "dedupe_key": row.dedupe_key,
                "ticker": row.ticker,
                "side": row.side,
                "notional": row.notional,
                "quantity": row.quantity,
                "price": row.price,
                "reason": row.reason,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]
        self.client.table("paper_orders").upsert(payload, on_conflict="dedupe_key").execute()

    def save_equity_snapshot(self, row: EquitySnapshot) -> None:
        self.client.table("equity_snapshots").insert(
            {
                "run_id": row.run_id,
                "ts": row.ts.isoformat(),
                "cash_balance": row.cash_balance,
                "exposure": row.exposure,
                "equity": row.equity,
            }
        ).execute()

    def fetch_latest_allocation(self) -> dict[str, float]:
        rows = self.client.table("portfolio_allocation").select("ticker,assigned_stack,is_active").execute().data or []
        return {row["ticker"]: float(row["assigned_stack"]) for row in rows if row.get("is_active")}

    def fetch_runtime_flag(self, flag_name: str, default: bool) -> bool:
        rows = self.client.table("runtime_flags").select("value_bool").eq("flag_name", flag_name).limit(1).execute().data or []
        if not rows:
            return default
        value = rows[0].get("value_bool")
        return bool(default if value is None else value)

    def fetch_pair_overrides(self) -> dict[str, PairOverride]:
        try:
            rows = self.client.table("pair_overrides").select("*").execute().data or []
        except Exception:
            return {}
        output: dict[str, PairOverride] = {}
        for row in rows:
            ticker = row.get("ticker")
            if not ticker:
                continue
            output[ticker] = PairOverride(
                ticker=ticker,
                enabled=bool(row.get("enabled", False)),
                block_new_entries=bool(row.get("block_new_entries", False)),
                force_close=bool(row.get("force_close", False)),
                assigned_stack_override=float(row["assigned_stack_override"]) if row.get("assigned_stack_override") is not None else None,
                tranche1_pct=float(row["tranche1_pct"]) if row.get("tranche1_pct") is not None else None,
                tranche2_pct=float(row["tranche2_pct"]) if row.get("tranche2_pct") is not None else None,
                tranche3_pct=float(row["tranche3_pct"]) if row.get("tranche3_pct") is not None else None,
                initial_stop_atr_multiple=float(row["initial_stop_atr_multiple"]) if row.get("initial_stop_atr_multiple") is not None else None,
                trail_stop_atr_multiple=float(row["trail_stop_atr_multiple"]) if row.get("trail_stop_atr_multiple") is not None else None,
                max_stale_position_hours=float(row["max_stale_position_hours"]) if row.get("max_stale_position_hours") is not None else None,
                notes=row.get("notes"),
            )
        return output

    def upsert_pair_override(self, override: PairOverride) -> None:
        payload = {
            "ticker": override.ticker,
            "enabled": override.enabled,
            "block_new_entries": override.block_new_entries,
            "force_close": override.force_close,
            "assigned_stack_override": override.assigned_stack_override,
            "tranche1_pct": override.tranche1_pct,
            "tranche2_pct": override.tranche2_pct,
            "tranche3_pct": override.tranche3_pct,
            "initial_stop_atr_multiple": override.initial_stop_atr_multiple,
            "trail_stop_atr_multiple": override.trail_stop_atr_multiple,
            "max_stale_position_hours": override.max_stale_position_hours,
            "notes": override.notes,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.client.table("pair_overrides").upsert(payload, on_conflict="ticker").execute()


def _parse_ts(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    if value.endswith("Z"):
        value = value.replace("Z", "+00:00")
    return datetime.fromisoformat(value)
