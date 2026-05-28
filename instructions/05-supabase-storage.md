# Supabase Storage

## Existing Tables

- `market_snapshots`
- `bot_metrics`
- `portfolio_allocation`
- `portfolio_decisions`
- `positions`

## Migration V2 Additions

- `bot_runs` for run idempotency and status audit.
- `paper_orders` for simulated order journal.
- `position_legs` for pyramid leg history.
- `equity_snapshots` for cash/exposure/equity timeline.
- `runtime_flags` for kill switch and runtime toggles.

## Security

- Keep RLS enabled on all tables.
- No public policies in MVP.
- Use service role key only in server-side jobs and dashboard runtime.

## Repository Contract

Python repository must support:

- run create/update with unique bucket key,
- snapshot and metrics writes,
- allocation read/write,
- positions/orders/equity persistence,
- runtime flag read.
