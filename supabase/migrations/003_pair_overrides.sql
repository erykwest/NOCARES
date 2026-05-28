-- Pair-level strategy and money management overrides.

create table if not exists public.pair_overrides (
  ticker text primary key,
  enabled boolean not null default false,
  block_new_entries boolean not null default false,
  force_close boolean not null default false,
  assigned_stack_override numeric,
  tranche1_pct numeric,
  tranche2_pct numeric,
  tranche3_pct numeric,
  initial_stop_atr_multiple numeric,
  trail_stop_atr_multiple numeric,
  max_stale_position_hours numeric,
  notes text,
  updated_at timestamptz not null default now()
);

alter table public.pair_overrides enable row level security;
