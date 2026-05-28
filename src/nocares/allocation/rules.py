from __future__ import annotations

from collections.abc import Iterable

from nocares.domain import (
    AllocationPlan,
    AssignedStack,
    CloseCommand,
    CoinMetrics,
    EmergencyReserveTarget,
    PositionStatus,
    Regime,
    enum_value,
)


def build_allocation_plan(
    metrics: Iterable[CoinMetrics],
    *,
    total_stack: float = 100.0,
    reserve_pct: float = 0.20,
    active_coin_slots: int = 4,
    min_coin_pct: float = 0.05,
    max_coin_pct: float = 0.30,
    emergency_min_pct: float = 0.05,
    emergency_max_pct: float = 0.20,
    max_stale_position_hours: float = 4.0,
) -> AllocationPlan:
    """Build a deterministic allocation plan from compact coin metrics."""
    metric_list = list(metrics)
    reserve_wallet = round(total_stack * reserve_pct, 8)
    investable_stack = total_stack - reserve_wallet
    min_stack = total_stack * min_coin_pct
    max_stack = total_stack * max_coin_pct

    ranked = sorted(metric_list, key=_score_metric, reverse=True)
    selected = ranked[:active_coin_slots]

    # If fewer than the target slots exist, keep the unassignable capital in reserve.
    effective_investable = min(investable_stack, max_stack * len(selected))
    if selected:
        allocations = _capped_weighted_allocation(
            [_score_metric(item) for item in selected],
            effective_investable,
            min_stack,
            max_stack,
        )
    else:
        allocations = []

    leftover = investable_stack - sum(allocations)
    reserve_wallet = round(reserve_wallet + max(0.0, leftover), 8)

    assigned = tuple(
        AssignedStack(
            ticker=item.ticker,
            stack_size=round(size, 8),
            status=_status_for_metric(item),
            reason=_reason_for_metric(item),
        )
        for item, size in zip(selected, allocations, strict=True)
    )

    selected_tickers = {item.ticker for item in selected}
    close_positions = tuple(
        CloseCommand(
            ticker=item.ticker,
            reason="Position stale or no longer in top allocation set.",
        )
        for item in metric_list
        if _should_close_stale(item, selected_tickers, max_stale_position_hours)
    )

    emergency_targets = tuple(
        EmergencyReserveTarget(
            ticker=item.ticker,
            max_draw_from_reserve=round(
                _reserve_draw_for_score(
                    _score_metric(item),
                    total_stack * emergency_min_pct,
                    total_stack * emergency_max_pct,
                ),
                8,
            ),
            trigger_condition="ADX > 25 and volume_delta improves versus previous 15m window.",
        )
        for item in ranked
        if item.ticker not in selected_tickers and item.is_flat and _score_metric(item) >= 25
    )[:2]

    return AllocationPlan(
        total_stack=total_stack,
        reserve_wallet=reserve_wallet,
        assigned_stacks=assigned,
        close_positions=close_positions,
        emergency_reserve_targets=emergency_targets,
    )


def validate_allocation_plan(
    plan: AllocationPlan,
    *,
    reserve_pct: float = 0.20,
    min_coin_pct: float = 0.05,
    max_coin_pct: float = 0.30,
    active_coin_slots: int = 4,
) -> None:
    """Raise ValueError if the plan violates hard portfolio constraints."""
    min_reserve = plan.total_stack * reserve_pct
    min_coin = plan.total_stack * min_coin_pct
    max_coin = plan.total_stack * max_coin_pct

    if plan.reserve_wallet + 1e-9 < min_reserve:
        raise ValueError("reserve_wallet is below the hard reserve limit")
    if len(plan.assigned_stacks) > active_coin_slots:
        raise ValueError("too many active coin allocations")
    for item in plan.assigned_stacks:
        if item.stack_size + 1e-9 < min_coin:
            raise ValueError(f"{item.ticker} allocation is below minimum")
        if item.stack_size - 1e-9 > max_coin:
            raise ValueError(f"{item.ticker} allocation is above maximum")
    if plan.reserve_wallet + plan.allocated_stack - plan.total_stack > 1e-6:
        raise ValueError("reserve plus allocations exceeds total stack")


def _score_metric(metric: CoinMetrics) -> float:
    if metric.score is not None:
        return metric.score

    regime_bonus = {
        Regime.TREND_UP.value: 10.0,
        Regime.TREND_DOWN.value: 6.0,
        Regime.TRANSITION.value: 2.0,
        Regime.RANGE.value: -8.0,
    }.get(enum_value(metric.current_regime), 0.0)
    position_bonus = 4.0 if not metric.is_flat and metric.unrealized_pnl_pct > 0 else 0.0
    stale_penalty = max(0.0, metric.position_duration_hours - 3.0) * 2.0

    return (
        metric.adx * 0.8
        + metric.volume_delta * 0.25
        + metric.book_imbalance * 12.0
        + metric.unrealized_pnl_pct * 1.5
        + regime_bonus
        + position_bonus
        - stale_penalty
    )


def _capped_weighted_allocation(
    scores: list[float],
    investable_stack: float,
    min_stack: float,
    max_stack: float,
) -> list[float]:
    if not scores:
        return []

    count = len(scores)
    minimum_total = min_stack * count
    if investable_stack < minimum_total:
        return [investable_stack / count] * count

    allocations = [min_stack] * count
    remaining = investable_stack - minimum_total
    active = set(range(count))
    weights = [max(score, 0.01) for score in scores]

    while remaining > 1e-9 and active:
        total_weight = sum(weights[index] for index in active)
        proposed = []
        for index in active:
            share = remaining * (weights[index] / total_weight)
            proposed.append((index, min(share, max_stack - allocations[index])))

        added = 0.0
        capped = set()
        for index, amount in proposed:
            if amount <= 1e-9:
                capped.add(index)
                continue
            allocations[index] += amount
            added += amount
            if max_stack - allocations[index] <= 1e-9:
                capped.add(index)

        active -= capped
        remaining -= added
        if added <= 1e-9:
            break

    return allocations


def _status_for_metric(metric: CoinMetrics) -> str:
    if enum_value(metric.position_status) != PositionStatus.FLAT.value:
        return "HOLD_POSITION"
    if enum_value(metric.current_regime) in {Regime.TREND_UP.value, Regime.TREND_DOWN.value}:
        return "ALLOW_TRADING"
    return "WATCH_ONLY"


def _reason_for_metric(metric: CoinMetrics) -> str:
    score = _score_metric(metric)
    return (
        f"score={score:.2f}; regime={enum_value(metric.current_regime)}; "
        f"adx={metric.adx:.2f}; volume_delta={metric.volume_delta:.2f}"
    )


def _should_close_stale(
    metric: CoinMetrics,
    selected_tickers: set[str],
    max_stale_position_hours: float,
) -> bool:
    if metric.is_flat:
        return False
    if metric.ticker in selected_tickers:
        return False
    if metric.position_duration_hours < max_stale_position_hours:
        return False
    return enum_value(metric.current_regime) == Regime.RANGE.value or metric.unrealized_pnl_pct <= 0.5


def _reserve_draw_for_score(score: float, min_draw: float, max_draw: float) -> float:
    normalized = min(max((score - 25.0) / 30.0, 0.0), 1.0)
    return min_draw + (max_draw - min_draw) * normalized
