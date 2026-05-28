-- Runtime audit, paper execution journal and technical snapshot tables.

create table if not exists public.bot_runs (
  run_id text primary key,
  run_type text not null,
  bucket_ts timestamptz not null,
  status text not null default 'running',
  message text,
  started_at timestamptz not null default now(),
  ended_at timestamptz
);

create unique index if not exists bot_runs_type_bucket_unique
  on public.bot_runs (run_type, bucket_ts);

create table if not exists public.paper_orders (
  id bigserial primary key,
  run_id text not null references public.bot_runs(run_id) on delete cascade,
  dedupe_key text not null unique,
  ticker text not null,
  side text not null check (side in ('buy', 'sell')),
  notional numeric not null,
  quantity numeric not null,
  price numeric not null,
  reason text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.position_legs (
  id bigserial primary key,
  ticker text not null,
  run_id text not null references public.bot_runs(run_id) on delete cascade,
  tranche_index integer not null check (tranche_index in (1, 2, 3)),
  notional numeric not null,
  quantity numeric not null,
  entry_price numeric not null,
  created_at timestamptz not null default now()
);

create table if not exists public.equity_snapshots (
  id bigserial primary key,
  run_id text not null references public.bot_runs(run_id) on delete cascade,
  ts timestamptz not null,
  cash_balance numeric not null,
  exposure numeric not null,
  equity numeric not null
);

create table if not exists public.runtime_flags (
  flag_name text primary key,
  value_bool boolean not null default false,
  updated_at timestamptz not null default now()
);

insert into public.runtime_flags(flag_name, value_bool)
values ('paper_trading_enabled', true)
on conflict (flag_name) do nothing;

create table if not exists public.technical_snapshots (
  id bigserial primary key,
  ticker text not null,
  timeframe text not null,
  ts timestamptz not null,
  price numeric not null,
  volume numeric not null,
  ema_fast numeric,
  ema_slow numeric,
  atr numeric,
  adx numeric,
  momentum numeric,
  volume_ratio numeric,
  current_regime text not null,
  score numeric not null,
  created_at timestamptz not null default now()
);

create index if not exists technical_snapshots_ticker_ts_idx
  on public.technical_snapshots (ticker, ts desc);

alter table public.positions
  add column if not exists highest_price numeric;

alter table public.positions
  add column if not exists quantity numeric;

alter table public.positions
  add column if not exists invested_notional numeric;

create unique index if not exists positions_ticker_unique_idx
  on public.positions (ticker);

alter table public.bot_runs enable row level security;
alter table public.paper_orders enable row level security;
alter table public.position_legs enable row level security;
alter table public.equity_snapshots enable row level security;
alter table public.runtime_flags enable row level security;
alter table public.technical_snapshots enable row level security;
