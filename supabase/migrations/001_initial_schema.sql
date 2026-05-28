-- Initial schema for NOCARES.
-- Designed for compact aggregated data, not raw tick-by-tick storage.

create table if not exists public.market_snapshots (
  id bigserial primary key,
  ticker text not null,
  timeframe text not null,
  ts timestamptz not null,
  price numeric,
  volume numeric,
  volume_delta numeric,
  book_imbalance numeric,
  adx numeric,
  atr numeric,
  current_regime text not null default 'range',
  created_at timestamptz not null default now()
);

create index if not exists market_snapshots_ticker_ts_idx
  on public.market_snapshots (ticker, ts desc);

create table if not exists public.bot_metrics (
  ticker text primary key,
  updated_at timestamptz not null default now(),
  adx numeric not null default 0,
  atr numeric not null default 0,
  volume_delta numeric not null default 0,
  book_imbalance numeric not null default 0,
  current_regime text not null default 'range',
  position_status text not null default 'flat',
  position_duration_hours numeric not null default 0,
  unrealized_pnl_pct numeric not null default 0,
  score numeric,
  correlation_group text
);

create table if not exists public.portfolio_allocation (
  ticker text primary key,
  updated_at timestamptz not null default now(),
  assigned_stack numeric not null default 0,
  is_active boolean not null default false,
  emergency_reserve_allowed numeric not null default 0,
  status text not null default 'STAY_FLAT',
  reason text
);

create table if not exists public.portfolio_decisions (
  id bigserial primary key,
  decided_at timestamptz not null default now(),
  total_stack numeric not null,
  reserve_wallet numeric not null,
  payload jsonb not null,
  source text not null default 'llm'
);

create table if not exists public.positions (
  id bigserial primary key,
  ticker text not null,
  side text not null check (side in ('long', 'short')),
  status text not null default 'open',
  assigned_stack numeric not null default 0,
  tranche_status text not null default 'tranche_1',
  average_entry_price numeric,
  stop_price numeric,
  opened_at timestamptz not null default now(),
  closed_at timestamptz,
  realized_pnl_pct numeric
);

create index if not exists positions_ticker_status_idx
  on public.positions (ticker, status);

-- Keep tables closed by default. Server-side jobs should use a privileged
-- connection or explicit policies added in later migrations.
alter table public.market_snapshots enable row level security;
alter table public.bot_metrics enable row level security;
alter table public.portfolio_allocation enable row level security;
alter table public.portfolio_decisions enable row level security;
alter table public.positions enable row level security;
