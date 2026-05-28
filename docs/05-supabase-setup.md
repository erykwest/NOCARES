# Supabase Setup

Project: `NOCARES`

Project id: `dhaphungvlbbijfpwbuo`

Region: `eu-west-1`

Postgres: `17`

## Stato iniziale

La migrazione `initial_schema` crea:

- `public.market_snapshots`
- `public.bot_metrics`
- `public.portfolio_allocation`
- `public.portfolio_decisions`
- `public.positions`

La migrazione `002_runtime_and_paper_tables` aggiunge:

- `public.bot_runs`
- `public.paper_orders`
- `public.position_legs`
- `public.equity_snapshots`
- `public.runtime_flags`
- `public.technical_snapshots`

La migrazione `003_pair_overrides` aggiunge:

- `public.pair_overrides`

Tutte le tabelle hanno RLS attiva e nessuna policy pubblica. Per ora e voluto: il bot deve usare una connessione server-side o service role, non chiavi esposte nel client.

## Advisor attesi

Supabase puo segnalare:

- `RLS Enabled No Policy`: atteso finche non decidiamo un modello di accesso client.
- `Unused Index`: atteso su database vuoto.

Non salvare password o service role key in repository. Usa `.env` locale, che e ignorato da Git.
