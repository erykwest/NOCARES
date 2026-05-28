# Risk And Paper Execution

## Portfolio Rules

- Reserve wallet minimum: 20% of total stack.
- Max active symbols: 4.
- Per-symbol allocation: 5% to 30%.
- Max portfolio exposure: 80%.

## Position Rules

- Long only.
- Pyramid tranches: `50%`, `30%`, `20%` of assigned symbol stack.
- Tranche 2 and 3 require favorable movement and valid regime.

## Stops

- Initial stop: `entry - initial_stop_atr_multiple * ATR`.
- Trailing stop: `highest_close - trail_stop_atr_multiple * ATR`.
- After tranche 2, move stop to at least breakeven when possible.

## Exit Conditions

- Stop hit.
- Position stale over configured hours with weak score/regime.
- Kill switch conditions (drawdown/trade caps) triggered.

## Paper Accounting

- Record every simulated order in `paper_orders`.
- Persist open/closed positions and equity snapshots.
