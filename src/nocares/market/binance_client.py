from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import time
from urllib import parse, request
from urllib.error import HTTPError, URLError

from nocares.domain import Candle


def normalize_pair_symbol(pair: str) -> str:
    """Convert configured pair format like BTC/USDT into Binance symbol BTCUSDT."""
    return pair.replace("/", "").upper().strip()


@dataclass
class BinanceMarketClient:
    base_url: str = "https://api.binance.com"
    timeout_seconds: int = 10
    max_retries: int = 3
    request_pause_ms: int = 100
    use_mock: bool = False

    def fetch_klines(self, pair: str, interval: str, limit: int = 120) -> list[Candle]:
        symbol = normalize_pair_symbol(pair)
        if self.use_mock:
            return _mock_klines(symbol, interval, limit)

        endpoint = f"{self.base_url.rstrip('/')}/api/v3/klines"
        params = parse.urlencode({"symbol": symbol, "interval": interval, "limit": limit})
        url = f"{endpoint}?{params}"

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                req = request.Request(url=url, method="GET")
                with request.urlopen(req, timeout=self.timeout_seconds) as response:
                    payload = response.read().decode("utf-8")
                    rows = json.loads(payload)
                    candles = [_row_to_candle(symbol, row) for row in rows]
                    return [item for item in candles if item.close_price > 0]
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
                last_error = exc
                time.sleep((self.request_pause_ms / 1000.0) * attempt)

        raise RuntimeError(f"binance klines fetch failed for {symbol} {interval}: {last_error}")


def _row_to_candle(symbol: str, row: list) -> Candle:
    return Candle(
        symbol=symbol,
        open_time=datetime.fromtimestamp(row[0] / 1000.0, tz=timezone.utc),
        close_time=datetime.fromtimestamp(row[6] / 1000.0, tz=timezone.utc),
        open_price=float(row[1]),
        high_price=float(row[2]),
        low_price=float(row[3]),
        close_price=float(row[4]),
        volume=float(row[5]),
    )


def _mock_klines(symbol: str, interval: str, limit: int) -> list[Candle]:
    minutes_map = {"5m": 5, "15m": 15, "1h": 60}
    step = minutes_map.get(interval, 5)
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    price = 100 + (sum(ord(ch) for ch in symbol) % 50)
    candles: list[Candle] = []

    for index in range(limit):
        position = limit - index
        open_time = now - timedelta(minutes=step * position)
        close_time = open_time + timedelta(minutes=step) - timedelta(milliseconds=1)
        drift = 0.15 * (1 if index % 9 != 0 else -1)
        base = price + drift * index
        high = base * 1.002
        low = base * 0.998
        close = base * (1.0 + (0.0006 if index % 3 else -0.0003))
        volume = 1000 + (index * 7)
        candles.append(
            Candle(
                symbol=symbol,
                open_time=open_time,
                close_time=close_time,
                open_price=base,
                high_price=high,
                low_price=low,
                close_price=close,
                volume=volume,
            )
        )
    return candles
