# Indicators And Signals

## Required Indicators

- EMA fast = 21 periods.
- EMA slow = 50 periods.
- ATR = 14 periods.
- ADX = 14 periods.
- Momentum over configurable lookback windows.
- Volume ratio vs rolling mean.

## Regime Classification

- `range` if `ADX < 20`.
- `transition` if `20 <= ADX < 25`.
- `trend_up` if `ADX >= 25` and fast EMA above slow EMA.

## Signal Policy

- New entries allowed only in `trend_up`.
- `range` and `transition` are no-entry states.
- Signal generation must be deterministic.

## Score

- Score combines trend strength, momentum, volume and a volatility penalty.
- Score output is persisted per symbol and used by allocation/rebalance.
