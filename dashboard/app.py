from __future__ import annotations

from datetime import datetime
import os

import streamlit as st


def main() -> None:
    st.set_page_config(page_title="NOCARES Dashboard", layout="wide")
    st.title("NOCARES - Paper Trading Cockpit")

    if not _authenticated():
        st.stop()

    with st.sidebar:
        st.header("Controls")
        row_limit = st.slider("Rows per table", min_value=20, max_value=300, value=100, step=20)
        only_open = st.checkbox("Only open positions", value=True)
        manual_refresh = st.button("Refresh now")
        if manual_refresh:
            st.rerun()

    client = _build_client()
    if client is None:
        st.warning("Supabase client not configured. Showing empty state.")
        _render_empty()
        return

    bot_runs = _select_rows(client, "bot_runs", "run_id,run_type,bucket_ts,status,message,started_at,ended_at", row_limit)
    positions = _select_rows(client, "positions", "ticker,status,tranche_status,average_entry_price,quantity,stop_price,highest_price,realized_pnl_pct,opened_at,closed_at,assigned_stack", row_limit)
    orders = _select_rows(client, "paper_orders", "ticker,side,notional,quantity,price,reason,created_at,run_id", row_limit)
    equity = _select_rows(client, "equity_snapshots", "ts,cash_balance,exposure,equity,run_id", row_limit)
    metrics = _select_rows(client, "bot_metrics", "ticker,adx,atr,volume_delta,current_regime,score,updated_at", row_limit)
    allocations = _select_rows(client, "portfolio_allocation", "ticker,assigned_stack,is_active,status,reason,updated_at", row_limit)
    runtime_flags = _select_rows(client, "runtime_flags", "flag_name,value_bool,updated_at", row_limit)
    technical = _select_rows(client, "technical_snapshots", "ticker,price,ts,timeframe", row_limit)

    positions_view = [row for row in positions if row.get("status") == "open"] if only_open else positions
    latest_price = _latest_price_map(technical)
    realized_pct, unrealized_pct, unrealized_notional = _pnl_summary(positions, latest_price)
    runs_sorted = sorted(bot_runs, key=lambda x: x.get("started_at") or "", reverse=True)
    latest_run = runs_sorted[0] if runs_sorted else None
    last_status = latest_run.get("status", "n/a") if latest_run else "n/a"
    status_badge = _status_badge(last_status)

    st.caption(f"Last run status: {status_badge}  |  Updated: {datetime.utcnow().isoformat(timespec='seconds')} UTC")
    _render_summary(
        equity=equity,
        positions=positions_view,
        orders=orders,
        bot_runs=runs_sorted,
        realized_pct=realized_pct,
        unrealized_pct=unrealized_pct,
    )

    overview_tab, positions_tab, orders_tab, metrics_tab, allocation_tab, runs_tab, operator_tab = st.tabs(
        ["Overview", "Positions", "Orders", "Metrics", "Allocation", "Runs", "Operator"]
    )

    with overview_tab:
        st.subheader("Equity")
        if equity:
            chart_data = _equity_series(equity)
            st.line_chart(chart_data)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Latest Cash", f"{float(equity[-1]['cash_balance']):.2f}")
            c2.metric("Latest Exposure", f"{float(equity[-1]['exposure']):.2f}")
            c3.metric("Latest Equity", f"{float(equity[-1]['equity']):.2f}")
            c4.metric("Unrealized Notional", f"{unrealized_notional:.2f}")
        else:
            st.info("No equity snapshots yet.")

        st.subheader("Runtime Flags")
        if runtime_flags:
            st.dataframe(runtime_flags, use_container_width=True)
        else:
            st.info("No runtime flags rows available.")

    with positions_tab:
        st.subheader("Positions")
        if positions_view:
            st.caption(f"Latest realized PnL % (closed): {realized_pct:.2f} | Unrealized PnL % (open): {unrealized_pct:.2f}")
            st.dataframe(positions_view, use_container_width=True)
        else:
            st.info("No positions for the selected filter.")

    with orders_tab:
        st.subheader("Recent Orders")
        if orders:
            st.dataframe(orders, use_container_width=True)
            buy_count = len([x for x in orders if x.get("side") == "buy"])
            sell_count = len([x for x in orders if x.get("side") == "sell"])
            st.caption(f"Buys: {buy_count} | Sells: {sell_count}")
        else:
            st.info("No paper orders yet.")

    with metrics_tab:
        st.subheader("Latest Metrics")
        if metrics:
            ranking = sorted(metrics, key=lambda x: float(x.get("score") or 0), reverse=True)
            st.dataframe(ranking, use_container_width=True)
        else:
            st.info("No bot metrics yet.")

    with allocation_tab:
        st.subheader("Portfolio Allocation")
        if allocations:
            st.dataframe(allocations, use_container_width=True)
        else:
            st.info("No allocation rows available.")

    with runs_tab:
        st.subheader("Run Log")
        if runs_sorted:
            st.dataframe(runs_sorted, use_container_width=True)
        else:
            st.info("No run rows yet.")

    with operator_tab:
        st.subheader("Operator Panel")
        _render_runtime_flag_operator(client, runtime_flags)


def _authenticated() -> bool:
    expected = (
        st.secrets.get("DASHBOARD_PASSWORD")
        if "DASHBOARD_PASSWORD" in st.secrets
        else os.getenv("DASHBOARD_PASSWORD")
    )
    if not expected:
        st.warning("Set DASHBOARD_PASSWORD in Streamlit secrets or environment.")
        return False

    if st.session_state.get("dash_auth") is True:
        return True

    entered = st.text_input("Dashboard password", type="password")
    if entered and entered == expected:
        st.session_state["dash_auth"] = True
        st.rerun()
    if entered and entered != expected:
        st.error("Invalid password.")
    return False


def _build_client():
    url = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL"))
    key = st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    if not url or not key:
        return None
    try:
        from supabase import create_client
    except ImportError:
        st.error("Install dependencies: pip install .[dashboard]")
        return None
    return create_client(url, key)


def _select_rows(client, table: str, fields: str, limit: int):
    try:
        response = client.table(table).select(fields).order("id", desc=True).limit(limit).execute()
        rows = response.data or []
        rows.reverse()
        return rows
    except Exception:
        # Some tables do not have an id or may be empty/missing before migration.
        try:
            response = client.table(table).select(fields).limit(limit).execute()
            return response.data or []
        except Exception:
            return []


def _render_summary(
    equity: list[dict],
    positions: list[dict],
    orders: list[dict],
    bot_runs: list[dict],
    realized_pct: float,
    unrealized_pct: float,
) -> None:
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    latest_equity = equity[-1]["equity"] if equity else 0
    open_positions = len([x for x in positions if x.get("status") == "open"])
    last_status = bot_runs[-1]["status"] if bot_runs else "n/a"
    c1.metric("Latest Equity", f"{latest_equity:.2f}")
    c2.metric("Open Positions", str(open_positions))
    c3.metric("Orders", str(len(orders)))
    c4.metric("Last Run", str(last_status))
    c5.metric("Closed PnL %", f"{realized_pct:.2f}")
    c6.metric("Open PnL %", f"{unrealized_pct:.2f}")


def _status_badge(status: str) -> str:
    normalized = (status or "").lower()
    if normalized == "success":
        return "SUCCESS"
    if normalized == "failed":
        return "FAILED"
    if normalized == "skipped":
        return "SKIPPED"
    return normalized.upper() if normalized else "N/A"


def _render_empty() -> None:
    st.info("No runtime backend available yet.")
    st.write(
        {
            "required": ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "DASHBOARD_PASSWORD"],
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


def _latest_price_map(technical_rows: list[dict]) -> dict[str, float]:
    latest: dict[str, tuple[str, float]] = {}
    for row in technical_rows:
        ticker = row.get("ticker")
        ts = row.get("ts") or ""
        price = float(row.get("price") or 0)
        if not ticker or price <= 0:
            continue
        prev = latest.get(ticker)
        if prev is None or ts > prev[0]:
            latest[ticker] = (ts, price)
    return {k: v[1] for k, v in latest.items()}


def _pnl_summary(positions: list[dict], latest_price: dict[str, float]) -> tuple[float, float, float]:
    closed = [row for row in positions if row.get("status") == "closed"]
    open_rows = [row for row in positions if row.get("status") == "open"]

    realized_values = [float(row.get("realized_pnl_pct") or 0) for row in closed if row.get("realized_pnl_pct") is not None]
    realized_pct = (sum(realized_values) / len(realized_values)) if realized_values else 0.0

    unrealized_pct_values: list[float] = []
    unrealized_notional = 0.0
    for row in open_rows:
        ticker = row.get("ticker")
        qty = float(row.get("quantity") or 0)
        entry = float(row.get("average_entry_price") or 0)
        if qty <= 0 or entry <= 0 or not ticker:
            continue
        mark = latest_price.get(ticker, float(row.get("highest_price") or entry))
        pct = ((mark - entry) / entry) * 100.0
        unrealized_pct_values.append(pct)
        unrealized_notional += (mark - entry) * qty

    unrealized_pct = (sum(unrealized_pct_values) / len(unrealized_pct_values)) if unrealized_pct_values else 0.0
    return realized_pct, unrealized_pct, unrealized_notional


def _equity_series(equity: list[dict]) -> dict[str, list[float]]:
    return {
        "equity": [float(row.get("equity") or 0) for row in equity],
        "cash_balance": [float(row.get("cash_balance") or 0) for row in equity],
        "exposure": [float(row.get("exposure") or 0) for row in equity],
    }


def _render_runtime_flag_operator(client, runtime_flags: list[dict]) -> None:
    current = False
    for row in runtime_flags:
        if row.get("flag_name") == "paper_trading_enabled":
            current = bool(row.get("value_bool"))
            break

    st.write({"paper_trading_enabled": current})
    allow_mutation = os.getenv("DASHBOARD_ALLOW_FLAG_MUTATION", "false").lower() in {"1", "true", "yes"}
    if not allow_mutation:
        st.info("Runtime flag mutation is disabled. Set DASHBOARD_ALLOW_FLAG_MUTATION=true to enable.")
        return

    target_value = st.toggle("Target paper_trading_enabled", value=current)
    expected = "ENABLE" if target_value else "DISABLE"
    confirmation = st.text_input(f'Type "{expected}" to confirm flag update')
    if st.button("Apply runtime flag change", type="primary"):
        if confirmation != expected:
            st.error("Confirmation text mismatch.")
            return
        payload = {
            "flag_name": "paper_trading_enabled",
            "value_bool": bool(target_value),
            "updated_at": datetime.utcnow().isoformat(timespec="seconds"),
        }
        try:
            client.table("runtime_flags").upsert(payload, on_conflict="flag_name").execute()
            st.success("Runtime flag updated.")
            st.rerun()
        except Exception as exc:  # pragma: no cover - UI feedback path
            st.error(f"Failed to update runtime flag: {exc}")


if __name__ == "__main__":
    main()
