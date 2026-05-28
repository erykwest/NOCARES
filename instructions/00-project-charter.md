# NOCARES Charter

## Name

NOCARES - Non-Custodial Crypto Allocation & Risk Engine System.

## Mission

Deliver a reproducible paper-trading platform for Binance Spot with a strict
separation between:

- deterministic execution logic (every 5 minutes),
- portfolio allocation logic (hourly),
- observability and operator controls.

## MVP Boundaries

- Paper trading only.
- Long only, no leverage.
- No order book streaming and no sub-minute execution loops.
- No live order submission to exchanges.

## Success Criteria

- One full 5-minute cycle runs from market fetch to persistence.
- Risk rules are enforced even if LLM output is malformed.
- Dashboard can show state on empty and populated databases.
- Every cycle is idempotent for the same time bucket.

## Non-Negotiable Rules

- No live trading in MVP.
- No leverage in MVP.
- No secrets in repository.
- No bypass of deterministic risk guardrails.
