from __future__ import annotations

from typing import Any

import pandas as pd


def generate_signal(data: dict[str, pd.DataFrame], params: dict[str, Any]) -> pd.DataFrame:
    close = data["close"]
    fast = int(params.get("fast", 20))
    slow = int(params.get("slow", 60))
    pullback_pct = float(params.get("pullback_pct", -0.04))

    ma_fast = close.rolling(fast).mean()
    ma_slow = close.rolling(slow).mean()
    pullback = close / close.rolling(fast).max() - 1.0
    signal = (close > ma_slow) & (close < ma_fast) & (pullback <= pullback_pct)
    return signal.fillna(False)
