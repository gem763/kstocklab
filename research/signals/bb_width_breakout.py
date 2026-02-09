from __future__ import annotations

from typing import Any

import pandas as pd


def generate_signal(data: dict[str, pd.DataFrame], params: dict[str, Any]) -> pd.DataFrame:
    close = data["close"]
    lookback = int(params.get("lookback", 20))
    width_q = float(params.get("width_q", 0.20))
    band_k = float(params.get("band_k", 2.0))

    ma = close.rolling(lookback).mean()
    std = close.rolling(lookback).std()
    upper = ma + band_k * std
    lower = ma - band_k * std
    width = (upper - lower) / ma.replace(0, pd.NA)
    width_cut = width.rolling(lookback).quantile(width_q)
    signal = (close > upper) & (width <= width_cut)
    return signal.fillna(False)
