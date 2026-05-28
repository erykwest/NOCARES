from __future__ import annotations

from datetime import datetime
import os

import streamlit as st


def main() -> None:
    st.set_page_config(page_title="NOCARES Dashboard", layout="wide")
    st.title("NOCARES - Paper Trading Cockpit")

    if not _authenticated():
        st.stop()

    client = _build_client()
    if client is None:
        st.warning("Supabase client not configured. Showing empty state.")
        _render_empty()
        return

    bot_runs = _select_rows(client, "bot_runs", "run_type,bucket_ts,status,message,started_at,ended_at", 30)
    positions = _select_rows(client, "positions", "ticker,status,tranche_status,average_entry_price,quantity,stop_price,highest_price,realized_pnl_pct,opened_at,closed_at", 50)
    orders = _select_rows(client, "paper_orders", "ticker,side,notional,quantity,price,reason,created_at,run_id", 100)
    equity = _select_rows(client, "equity_snapshots", "ts,cash_balance,exposure,equity,run_id", 300)
    metrics = _select_rows(client, "bot_metrics", "ticker,adx,atr,volume_delta,current_regime,score,updated_at", 50)
    allocations = _select_rows(client, "portfolio_allocation", "ticker,assigned_stack,is_active,status,reason,updated_at", 50)

    _render_summary(equity, positions, orders, bot_runs)
    st.subheader("Equity Curve")
    if equity:
        st.line_chart([row["equity"] for row in equity])
        st.dataframe(equity, use_container_width=True)
    else:
        st.info("No equity snapshots yet.")

    st.subheader("Open Positions")
    open_rows = [row for row in positions if row.get("status") == "open"]
    st.dataframe(open_rows if open_rows else [], use_container_width=True)

    st.subheader("Recent Orders")
    st.dataframe(orders if orders else [], use_container_width=True)

    st.subheader("Latest Metrics")
    st.dataframe(metrics if metrics else [], use_container_width=True)

    st.subheader("Portfolio Allocation")
    st.dataframe(allocations if allocations else [], use_container_width=True)

    st.subheader("Run Log")
    st.dataframe(bot_runs if bot_runs else [], use_container_width=True)


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


def _render_summary(equity: list[dict], positions: list[dict], orders: list[dict], bot_runs: list[dict]) -> None:
    c1, c2, c3, c4 = st.columns(4)
    latest_equity = equity[-1]["equity"] if equity else 0
    open_positions = len([x for x in positions if x.get("status") == "open"])
    last_status = bot_runs[-1]["status"] if bot_runs else "n/a"
    c1.metric("Latest Equity", f"{latest_equity:.2f}")
    c2.metric("Open Positions", str(open_positions))
    c3.metric("Orders", str(len(orders)))
    c4.metric("Last Run", str(last_status))


def _render_empty() -> None:
    st.info("No runtime backend available yet.")
    st.write(
        {
            "required": ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "DASHBOARD_PASSWORD"],
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


if __name__ == "__main__":
    main()
