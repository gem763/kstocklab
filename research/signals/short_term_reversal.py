from __future__ import annotations

from typing import Any

import pandas as pd


def generate_signal(data: dict[str, pd.DataFrame], params: dict[str, Any]) -> pd.DataFrame:
    close = data["close"]
    drop_days = int(params.get("drop_days", 3))
    drop_threshold = float(params.get("drop_threshold", -0.10))

    drop = close / close.shift(drop_days) - 1.0
    bounce = close > close.shift(1)
    signal = (drop <= drop_threshold) & bounce
    return signal.fillna(False)

