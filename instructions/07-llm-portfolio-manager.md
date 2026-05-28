# LLM Portfolio Manager

## Execution Window

- Run hourly, separate from 5-minute cycle.
- Never block the deterministic paper cycle.

## Modes

- Deterministic mode: always available fallback.
- LLM mode: optional, guarded by validation.

## Input/Output Contract

- Input: latest `bot_metrics`, current open positions, portfolio state.
- Output: JSON with reserve wallet, assigned stacks, close commands and optional emergency targets.

## Guardrails

- Validate output with strict numeric bounds.
- Reject invalid payloads and fallback to deterministic allocation.
- Persist decisions into `portfolio_decisions`.

## Safety

- LLM cannot bypass max exposure, stop logic, cooldown or drawdown limits.
