from __future__ import annotations

from typing import Any

import pandas as pd


def generate_signal(data: dict[str, pd.DataFrame], params: dict[str, Any]) -> pd.DataFrame:
    close = data["close"]
    high = data.get("high", close)
    volume = data.get("volume")
    amount = data.get("amount")

    lookback = int(params.get("lookback", 20))
    volume_window = int(params.get("volume_window", 20))
    volume_mult = float(params.get("volume_mult", 1.2))

    channel_high = high.shift(1).rolling(lookback).max()
    breakout = close >= channel_high

    liquidity = volume if volume is not None else amount
    if liquidity is None:
        return breakout.fillna(False)

    liquidity_ma = liquidity.rolling(volume_window).mean()
    liquidity_confirm = liquidity >= liquidity_ma * volume_mult
    signal = breakout & liquidity_confirm
    return signal.fillna(False)

