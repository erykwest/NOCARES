from __future__ import annotations

from statistics import mean

from nocares.domain import CoinMetrics, Regime, TechnicalSnapshot
from nocares.strategy.regime import classify_regime


def build_technical_snapshot(
    pair: str,
    timeframe: str,
    closes: list[float],
    highs: list[float],
    lows: list[float],
    volumes: list[float],
    ts,
    adx_range_threshold: float,
    adx_trend_threshold: float,
    momentum_lookback: int = 3,
    volume_ratio_window: int = 10,
) -> TechnicalSnapshot:
    if len(closes) < 20:
        return TechnicalSnapshot(
            ticker=pair,
            timeframe=timeframe,
            ts=ts,
            price=closes[-1],
            volume=volumes[-1],
            ema_fast=None,
            ema_slow=None,
            atr=None,
            adx=None,
            momentum=None,
            volume_ratio=None,
            regime=Regime.TRANSITION,
            score=0.0,
        )

    ema_fast = ema(closes, 21)
    ema_slow = ema(closes, 50)
    atr_v = atr(highs, lows, closes, 14)
    adx_v = adx(highs, lows, closes, 14)
    mom = momentum(closes, momentum_lookback)
    vol_ratio = volume_ratio(volumes, volume_ratio_window)
    regime = classify_regime(
        adx=adx_v,
        ema_fast=ema_fast,
        ema_slow=ema_slow,
        range_threshold=adx_range_threshold,
        trend_threshold=adx_trend_threshold,
    )
    score = _score_snapshot(adx_v, mom, vol_ratio, atr_v, closes[-1], regime)

    return TechnicalSnapshot(
        ticker=pair,
        timeframe=timeframe,
        ts=ts,
        price=closes[-1],
        volume=volumes[-1],
        ema_fast=ema_fast,
        ema_slow=ema_slow,
        atr=atr_v,
        adx=adx_v,
        momentum=mom,
        volume_ratio=vol_ratio,
        regime=regime,
        score=score,
    )


def build_coin_metrics(snapshot: TechnicalSnapshot) -> CoinMetrics:
    return CoinMetrics(
        ticker=snapshot.ticker,
        adx=snapshot.adx or 0.0,
        atr=snapshot.atr or 0.0,
        volume_delta=(snapshot.volume_ratio or 1.0) - 1.0,
        current_regime=snapshot.regime,
        score=snapshot.score,
    )


def ema(values: list[float], period: int) -> float:
    if not values:
        return 0.0
    multiplier = 2 / (period + 1)
    ema_val = values[0]
    for value in values[1:]:
        ema_val = (value - ema_val) * multiplier + ema_val
    return ema_val


def atr(highs: list[float], lows: list[float], closes: list[float], period: int) -> float:
    if len(highs) < 2 or len(lows) < 2 or len(closes) < 2:
        return 0.0

    true_ranges = []
    for idx in range(1, len(closes)):
        tr = max(
            highs[idx] - lows[idx],
            abs(highs[idx] - closes[idx - 1]),
            abs(lows[idx] - closes[idx - 1]),
        )
        true_ranges.append(tr)
    window = true_ranges[-period:] if len(true_ranges) >= period else true_ranges
    return mean(window) if window else 0.0


def adx(highs: list[float], lows: list[float], closes: list[float], period: int) -> float:
    if len(highs) <= period + 1:
        return 0.0

    plus_dm: list[float] = []
    minus_dm: list[float] = []
    trs: list[float] = []

    for idx in range(1, len(closes)):
        up_move = highs[idx] - highs[idx - 1]
        down_move = lows[idx - 1] - lows[idx]

        plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0.0)
        minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0.0)

        tr = max(
            highs[idx] - lows[idx],
            abs(highs[idx] - closes[idx - 1]),
            abs(lows[idx] - closes[idx - 1]),
        )
        trs.append(tr)

    if len(trs) < period:
        return 0.0

    dx_values: list[float] = []
    for idx in range(period, len(trs) + 1):
        tr_sum = sum(trs[idx - period : idx])
        if tr_sum == 0:
            continue
        plus_di = 100 * (sum(plus_dm[idx - period : idx]) / tr_sum)
        minus_di = 100 * (sum(minus_dm[idx - period : idx]) / tr_sum)
        denominator = plus_di + minus_di
        if denominator == 0:
            dx = 0.0
        else:
            dx = 100 * abs(plus_di - minus_di) / denominator
        dx_values.append(dx)

    if not dx_values:
        return 0.0
    window = dx_values[-period:] if len(dx_values) >= period else dx_values
    return mean(window)


def momentum(closes: list[float], lookback: int) -> float:
    if len(closes) <= lookback:
        return 0.0
    old = closes[-1 - lookback]
    if old == 0:
        return 0.0
    return (closes[-1] - old) / old


def volume_ratio(volumes: list[float], window: int) -> float:
    if not volumes:
        return 1.0
    lookback = volumes[-window:] if len(volumes) >= window else volumes
    baseline = mean(lookback)
    if baseline == 0:
        return 1.0
    return volumes[-1] / baseline


def _score_snapshot(
    adx_value: float,
    momentum_value: float,
    volume_ratio_value: float,
    atr_value: float,
    close_price: float,
    regime: Regime,
) -> float:
    trend_bonus = 8.0 if regime == Regime.TREND_UP else (-6.0 if regime == Regime.RANGE else 0.0)
    vol_penalty = 0.0 if close_price <= 0 else (atr_value / close_price) * 120.0
    return (
        adx_value * 0.7
        + momentum_value * 180.0
        + (volume_ratio_value - 1.0) * 35.0
        + trend_bonus
        - vol_penalty
    )
