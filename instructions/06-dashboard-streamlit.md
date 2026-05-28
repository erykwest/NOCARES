# Streamlit Dashboard

## Scope

- Read-only operational cockpit.
- No live trade buttons in MVP.

## Views

- Equity curve and latest equity values.
- Open positions and stop levels.
- Recent paper orders.
- Latest symbol metrics and ranking.
- Run log (`bot_runs`) with status.

## Empty State

- Dashboard must render cleanly with no data.
- Show "no rows yet" placeholders per panel.

## Access

- Gate access with `DASHBOARD_PASSWORD` via Streamlit Secrets.
- Never hardcode credentials in source.
