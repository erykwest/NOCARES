# Runtime: GitHub Actions

## Primary Scheduler

- Use GitHub Actions `schedule: "*/5 * * * *"` for paper cycle.
- Use a second hourly workflow for portfolio rebalance.

## Idempotency

- Compute bucket timestamp from UTC minute floor to 5m.
- Persist one `bot_runs` record per bucket and run type.
- Skip processing if the bucket already exists and completed.

## Required GitHub Secrets

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `OPENAI_API_KEY` (only when LLM mode is enabled)
- `DASHBOARD_PASSWORD` (for dashboard app)

## CLI Entry Points

- `py -m nocares.bot.cycle --mode paper --once`
- `py -m nocares.bot.rebalance --mode deterministic --once`

## Failure Policy

- Mark `bot_runs.status = failed` on hard failures.
- Never write duplicate paper orders for the same run.
