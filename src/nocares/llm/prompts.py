from __future__ import annotations

import json

from nocares.domain import CoinMetrics, enum_value


def build_allocation_prompt(
    metrics: list[CoinMetrics],
    *,
    total_stack: float = 100.0,
    reserve_pct: float = 0.20,
) -> str:
    """Build the compact prompt sent to the LLM allocation layer."""
    payload = {
        "task": "Allocate shared crypto portfolio for the next hour.",
        "hard_constraints": {
            "total_stack": total_stack,
            "reserve_wallet_min": total_stack * reserve_pct,
            "active_coin_slots": 4,
            "coin_stack_min": total_stack * 0.05,
            "coin_stack_max": total_stack * 0.30,
            "emergency_reserve_draw_min": total_stack * 0.05,
            "emergency_reserve_draw_max": total_stack * 0.20,
        },
        "output_contract": {
            "allocation_strategy": {
                "reserve_wallet": "number",
                "assigned_stacks": [
                    {
                        "ticker": "string",
                        "stack_size": "number",
                        "status": "ALLOW_TRADING | HOLD_POSITION | WATCH_ONLY",
                        "reason": "short string",
                    }
                ],
            },
            "commands": {
                "close_positions": [{"ticker": "string", "reason": "short string"}],
                "emergency_reserve_targets": [
                    {
                        "ticker": "string",
                        "max_draw_from_reserve": "number",
                        "trigger_condition": "short string",
                    }
                ],
            },
        },
        "metrics": [
            {
                "ticker": item.ticker,
                "adx": item.adx,
                "atr": item.atr,
                "volume_delta": item.volume_delta,
                "book_imbalance": item.book_imbalance,
                "current_regime": enum_value(item.current_regime),
                "position_status": enum_value(item.position_status),
                "position_duration_hours": item.position_duration_hours,
                "unrealized_pnl_pct": item.unrealized_pnl_pct,
                "score": item.score,
                "correlation_group": item.correlation_group,
            }
            for item in metrics
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True)
