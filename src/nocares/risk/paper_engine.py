from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from nocares.domain import (
    EquitySnapshot,
    PaperOrder,
    PositionLegState,
    PositionState,
    Regime,
    TechnicalSnapshot,
    enum_value,
)
from nocares.strategy.trailing_stop import long_trailing_stop


@dataclass(frozen=True)
class PaperEngineConfig:
    total_stack: float
    tranches: tuple[float, float, float]
    initial_stop_atr_multiple: float
    trail_stop_atr_multiple: float
    min_tranche2_move_atr: float
    min_tranche3_move_atr: float
    max_portfolio_exposure_pct: float
    max_stale_position_hours: float


@dataclass(frozen=True)
class PaperEngineResult:
    positions: list[PositionState]
    orders: list[PaperOrder]
    legs: list[PositionLegState]
    equity: EquitySnapshot


def execute_paper_cycle(
    *,
    run_id: str,
    run_ts: datetime,
    snapshots: dict[str, TechnicalSnapshot],
    allocations: dict[str, float],
    open_positions: list[PositionState],
    config: PaperEngineConfig,
) -> PaperEngineResult:
    positions_by_ticker = {row.ticker: row for row in open_positions}
    new_orders: list[PaperOrder] = []
    new_legs: list[PositionLegState] = []
    next_positions: dict[str, PositionState] = {}

    # Phase 1: update exits for existing positions.
    for ticker, position in positions_by_ticker.items():
        snap = snapshots.get(ticker)
        if not snap:
            next_positions[ticker] = position
            continue
        current_price = snap.price
        current_atr = max(snap.atr or 0.0, 1e-9)
        highest = max(position.highest_price, current_price)
        trailed_stop = long_trailing_stop(
            highest_price=highest,
            atr=current_atr,
            multiple=config.trail_stop_atr_multiple,
            current_stop=position.stop_price,
        )

        age_hours = max((run_ts - position.opened_at).total_seconds() / 3600.0, 0.0)
        stale_range = enum_value(snap.regime) == Regime.RANGE.value and age_hours >= config.max_stale_position_hours

        if current_price <= trailed_stop or stale_range:
            sell_order, closed = _close_position(
                run_id=run_id,
                run_ts=run_ts,
                ticker=ticker,
                position=position,
                price=current_price,
                reason="stop_hit" if current_price <= trailed_stop else "stale_range",
            )
            new_orders.append(sell_order)
            next_positions[ticker] = closed
            continue

        next_positions[ticker] = PositionState(
            ticker=position.ticker,
            side=position.side,
            status=position.status,
            assigned_stack=position.assigned_stack,
            tranche_status=position.tranche_status,
            average_entry_price=position.average_entry_price,
            quantity=position.quantity,
            invested_notional=position.invested_notional,
            stop_price=trailed_stop,
            highest_price=highest,
            opened_at=position.opened_at,
            closed_at=position.closed_at,
            realized_pnl_pct=position.realized_pnl_pct,
        )

    # Phase 2: entries and pyramid extensions.
    max_exposure = config.total_stack * (config.max_portfolio_exposure_pct / 100.0)
    current_exposure = _compute_exposure(next_positions.values(), snapshots)

    for ticker, assigned_stack in allocations.items():
        snap = snapshots.get(ticker)
        if not snap:
            continue
        if snap.regime != Regime.TREND_UP:
            continue

        pos = next_positions.get(ticker)
        if not pos or pos.status != "open":
            notional = assigned_stack * config.tranches[0]
            if current_exposure + notional > max_exposure or notional <= 0:
                continue
            order, position, leg = _open_new_position(
                run_id=run_id,
                run_ts=run_ts,
                ticker=ticker,
                assigned_stack=assigned_stack,
                notional=notional,
                price=snap.price,
                atr=max(snap.atr or 0.0, 1e-9),
                config=config,
            )
            current_exposure += notional
            new_orders.append(order)
            new_legs.append(leg)
            next_positions[ticker] = position
            continue

        next_tranche = _next_tranche_index(pos.tranche_status)
        if next_tranche is None:
            continue
        move_atr = (snap.price - pos.average_entry_price) / max(snap.atr or 0.0, 1e-9)
        min_move = config.min_tranche2_move_atr if next_tranche == 2 else config.min_tranche3_move_atr
        if move_atr < min_move:
            continue

        notional = assigned_stack * config.tranches[next_tranche - 1]
        if current_exposure + notional > max_exposure or notional <= 0:
            continue

        order, updated, leg = _add_tranche(
            run_id=run_id,
            run_ts=run_ts,
            ticker=ticker,
            position=pos,
            notional=notional,
            price=snap.price,
            tranche_index=next_tranche,
            atr=max(snap.atr or 0.0, 1e-9),
            config=config,
        )
        current_exposure += notional
        new_orders.append(order)
        new_legs.append(leg)
        next_positions[ticker] = updated

    positions_out = list(next_positions.values())
    exposure = _compute_exposure(positions_out, snapshots)
    cash = max(config.total_stack - exposure, 0.0)
    equity = EquitySnapshot(run_id=run_id, ts=run_ts, cash_balance=cash, exposure=exposure, equity=cash + exposure)

    return PaperEngineResult(positions=positions_out, orders=new_orders, legs=new_legs, equity=equity)


def _open_new_position(
    *,
    run_id: str,
    run_ts: datetime,
    ticker: str,
    assigned_stack: float,
    notional: float,
    price: float,
    atr: float,
    config: PaperEngineConfig,
) -> tuple[PaperOrder, PositionState, PositionLegState]:
    quantity = notional / max(price, 1e-9)
    stop = price - (atr * config.initial_stop_atr_multiple)
    order = PaperOrder(
        run_id=run_id,
        dedupe_key=f"{run_id}:{ticker}:buy:1",
        ticker=ticker,
        side="buy",
        notional=notional,
        quantity=quantity,
        price=price,
        reason="entry_tranche_1",
        created_at=run_ts,
    )
    position = PositionState(
        ticker=ticker,
        side="long",
        status="open",
        assigned_stack=assigned_stack,
        tranche_status="tranche_1",
        average_entry_price=price,
        quantity=quantity,
        invested_notional=notional,
        stop_price=stop,
        highest_price=price,
        opened_at=run_ts,
    )
    leg = PositionLegState(
        ticker=ticker,
        run_id=run_id,
        tranche_index=1,
        notional=notional,
        quantity=quantity,
        entry_price=price,
        created_at=run_ts,
    )
    return order, position, leg


def _add_tranche(
    *,
    run_id: str,
    run_ts: datetime,
    ticker: str,
    position: PositionState,
    notional: float,
    price: float,
    tranche_index: int,
    atr: float,
    config: PaperEngineConfig,
) -> tuple[PaperOrder, PositionState, PositionLegState]:
    quantity = notional / max(price, 1e-9)
    invested = position.invested_notional + notional
    total_qty = position.quantity + quantity
    avg_entry = invested / max(total_qty, 1e-9)
    stop_candidate = position.stop_price
    if tranche_index >= 2:
        stop_candidate = max(stop_candidate, avg_entry)
    stop_candidate = max(
        stop_candidate,
        price - (atr * config.trail_stop_atr_multiple),
    )
    updated = PositionState(
        ticker=position.ticker,
        side=position.side,
        status=position.status,
        assigned_stack=position.assigned_stack,
        tranche_status=f"tranche_{tranche_index}",
        average_entry_price=avg_entry,
        quantity=total_qty,
        invested_notional=invested,
        stop_price=stop_candidate,
        highest_price=max(position.highest_price, price),
        opened_at=position.opened_at,
        closed_at=position.closed_at,
        realized_pnl_pct=position.realized_pnl_pct,
    )
    order = PaperOrder(
        run_id=run_id,
        dedupe_key=f"{run_id}:{ticker}:buy:{tranche_index}",
        ticker=ticker,
        side="buy",
        notional=notional,
        quantity=quantity,
        price=price,
        reason=f"entry_tranche_{tranche_index}",
        created_at=run_ts,
    )
    leg = PositionLegState(
        ticker=ticker,
        run_id=run_id,
        tranche_index=tranche_index,
        notional=notional,
        quantity=quantity,
        entry_price=price,
        created_at=run_ts,
    )
    return order, updated, leg


def _close_position(
    *,
    run_id: str,
    run_ts: datetime,
    ticker: str,
    position: PositionState,
    price: float,
    reason: str,
) -> tuple[PaperOrder, PositionState]:
    notional = position.quantity * price
    pnl_pct = ((price - position.average_entry_price) / max(position.average_entry_price, 1e-9)) * 100.0
    order = PaperOrder(
        run_id=run_id,
        dedupe_key=f"{run_id}:{ticker}:sell",
        ticker=ticker,
        side="sell",
        notional=notional,
        quantity=position.quantity,
        price=price,
        reason=reason,
        created_at=run_ts,
    )
    closed = PositionState(
        ticker=position.ticker,
        side=position.side,
        status="closed",
        assigned_stack=position.assigned_stack,
        tranche_status=position.tranche_status,
        average_entry_price=position.average_entry_price,
        quantity=position.quantity,
        invested_notional=position.invested_notional,
        stop_price=position.stop_price,
        highest_price=max(position.highest_price, price),
        opened_at=position.opened_at,
        closed_at=run_ts,
        realized_pnl_pct=pnl_pct,
    )
    return order, closed


def _next_tranche_index(tranche_status: str) -> int | None:
    mapping = {
        "tranche_1": 2,
        "tranche_2": 3,
        "tranche_3": None,
    }
    return mapping.get(tranche_status, None)


def _compute_exposure(positions: Iterable[PositionState], snapshots: dict[str, TechnicalSnapshot]) -> float:
    total = 0.0
    for pos in positions:
        if pos.status != "open":
            continue
        mark = snapshots.get(pos.ticker)
        price = mark.price if mark else pos.average_entry_price
        total += pos.quantity * price
    return total
