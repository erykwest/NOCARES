from __future__ import annotations

from typing import Any


def validate_llm_payload(
    payload: dict[str, Any],
    *,
    total_stack: float = 100.0,
    reserve_pct: float = 0.20,
    min_coin_pct: float = 0.05,
    max_coin_pct: float = 0.30,
    active_coin_slots: int = 4,
) -> None:
    """Validate raw JSON-like LLM output before it can reach bot state."""
    strategy = payload.get("allocation_strategy")
    if not isinstance(strategy, dict):
        raise ValueError("missing allocation_strategy")

    reserve_wallet = float(strategy.get("reserve_wallet", 0))
    if reserve_wallet + 1e-9 < total_stack * reserve_pct:
        raise ValueError("reserve_wallet below required reserve")

    assigned = strategy.get("assigned_stacks", [])
    if len(assigned) > active_coin_slots:
        raise ValueError("too many assigned stacks")

    min_stack = total_stack * min_coin_pct
    max_stack = total_stack * max_coin_pct
    allocated = 0.0
    for item in assigned:
        stack_size = float(item["stack_size"])
        if stack_size + 1e-9 < min_stack:
            raise ValueError(f"{item.get('ticker')} below min allocation")
        if stack_size - 1e-9 > max_stack:
            raise ValueError(f"{item.get('ticker')} above max allocation")
        allocated += stack_size

    if allocated + reserve_wallet - total_stack > 1e-6:
        raise ValueError("allocated stack plus reserve exceeds total stack")
