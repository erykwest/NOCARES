from __future__ import annotations

import json
from typing import Any

from nocares.domain import AllocationPlan, AssignedStack, CloseCommand, EmergencyReserveTarget
from nocares.llm.guardrails import validate_llm_payload
from nocares.llm.prompts import build_allocation_prompt


def request_llm_allocation(
    *,
    metrics,
    total_stack: float,
    reserve_pct: float,
    model: str,
    api_key: str,
) -> dict[str, Any]:
    """Request LLM allocation JSON contract from OpenAI API."""
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("openai dependency is required for llm allocation mode") from exc

    client = OpenAI(api_key=api_key)
    prompt = build_allocation_prompt(metrics, total_stack=total_stack, reserve_pct=reserve_pct)
    response = client.responses.create(
        model=model,
        input=(
            "Return only JSON that matches output_contract. "
            "Do not include markdown fences.\n\n"
            f"{prompt}"
        ),
        temperature=0,
    )

    raw = response.output_text.strip()
    payload = json.loads(raw)
    validate_llm_payload(payload, total_stack=total_stack, reserve_pct=reserve_pct)
    return payload


def allocation_plan_from_payload(payload: dict[str, Any], total_stack: float) -> AllocationPlan:
    strategy = payload["allocation_strategy"]
    assigned = tuple(
        AssignedStack(
            ticker=item["ticker"],
            stack_size=float(item["stack_size"]),
            status=item.get("status", "WATCH_ONLY"),
            reason=item.get("reason", "llm"),
        )
        for item in strategy.get("assigned_stacks", [])
    )
    close_positions = tuple(
        CloseCommand(ticker=item["ticker"], reason=item.get("reason", "llm_close"))
        for item in payload.get("commands", {}).get("close_positions", [])
    )
    emergency_targets = tuple(
        EmergencyReserveTarget(
            ticker=item["ticker"],
            max_draw_from_reserve=float(item.get("max_draw_from_reserve", 0)),
            trigger_condition=item.get("trigger_condition", "llm"),
        )
        for item in payload.get("commands", {}).get("emergency_reserve_targets", [])
    )
    return AllocationPlan(
        total_stack=total_stack,
        reserve_wallet=float(strategy["reserve_wallet"]),
        assigned_stacks=assigned,
        close_positions=close_positions,
        emergency_reserve_targets=emergency_targets,
    )
