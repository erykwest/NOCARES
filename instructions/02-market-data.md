# Market Data Contract

## Source

- Binance Spot public REST API (`/api/v3/klines`).
- No private endpoints in MVP.

## Symbols

- Read tracked pairs from config (format `BTC/USDT`).
- Normalize to exchange symbol (`BTCUSDT`) before API calls.

## Timeframes

- Operational frame: `5m`.
- Context frames: `15m` and `1h`.

## Data Validation

- Ignore malformed rows.
- Reject candles with non-positive close price.
- Keep output ordered by ascending open time.

## Reliability

- Retry with short exponential backoff.
- Lightweight pacing between symbol requests.
- Fail one symbol without aborting the full cycle.
