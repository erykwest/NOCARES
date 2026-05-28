from __future__ import annotations

from nocares.domain import Regime


def classify_regime(
    *,
    adx: float,
    ema_fast: float | None = None,
    ema_slow: float | None = None,
    range_threshold: float = 20.0,
    trend_threshold: float = 25.0,
) -> Regime:
    """Classify market regime from compact indicators."""
    if adx < range_threshold:
        return Regime.RANGE
    if adx < trend_threshold:
        return Regime.TRANSITION
    if ema_fast is not None and ema_slow is not None:
        return Regime.TREND_UP if ema_fast >= ema_slow else Regime.TREND_DOWN
    return Regime.TREND_UP
