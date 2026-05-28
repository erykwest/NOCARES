# Testing And Acceptance

## Unit Tests

- Indicators: trend/range classification and insufficient data handling.
- Risk engine: tranche sizing, trailing stop monotonicity, stop exits.
- Allocation guardrails: reserve and per-coin bounds.
- Idempotency: duplicate run bucket does not duplicate orders.

## Dry Run Tests

- `py -m nocares.bot.cycle --mode paper --once --dry-run --mock`
- `py -m nocares.bot.rebalance --mode deterministic --once --dry-run --mock`

## Dashboard Smoke Test

- Import app module without crash.
- Render with empty repository data.

## Acceptance Criteria

- Full 5m cycle completes for tracked pairs and writes consistent state.
- Run/audit tables updated with success or failure status.
- No secrets in repo and no secret values in workflow logs.
