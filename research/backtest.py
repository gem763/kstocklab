from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _slice_by_range(
    df: pd.DataFrame, start_date: pd.Timestamp | None, end_date: pd.Timestamp | None
) -> pd.DataFrame:
    out = df
    if start_date is not None:
        out = out[out.index >= start_date]
    if end_date is not None:
        out = out[out.index <= end_date]
    return out


def _summarize(selected_returns: pd.DataFrame, hold_days: int) -> dict[str, Any]:
    trades = selected_returns.stack().dropna()
    num_trades = int(trades.shape[0])

    if selected_returns.empty:
        return {
            "num_trades": 0,
            "avg_return": 0.0,
            "hit_rate": 0.0,
            "sharpe": 0.0,
            "cagr": 0.0,
            "mdd": 0.0,
            "turnover": 0.0,
            "hold_days": hold_days,
        }

    daily = selected_returns.mean(axis=1, skipna=True).fillna(0.0)
    avg_return = float(trades.mean()) if num_trades else 0.0
    hit_rate = float((trades > 0).mean()) if num_trades else 0.0

    daily_std = float(daily.std(ddof=1))
    if daily_std > 0:
        sharpe = float(daily.mean() / daily_std * np.sqrt(252.0))
    else:
        sharpe = 0.0

    equity = (1.0 + daily).cumprod()
    if equity.empty:
        cagr = 0.0
        mdd = 0.0
    else:
        years = max(len(equity) / 252.0, 1.0 / 252.0)
        cagr = float(equity.iloc[-1] ** (1.0 / years) - 1.0)
        drawdown = equity / equity.cummax() - 1.0
        mdd = float(drawdown.min())

    trade_count_by_day = selected_returns.notna().sum(axis=1)
    n_tickers = max(selected_returns.shape[1], 1)
    turnover = float((trade_count_by_day / n_tickers).mean())

    return {
        "num_trades": num_trades,
        "avg_return": avg_return,
        "hit_rate": hit_rate,
        "sharpe": sharpe,
        "cagr": cagr,
        "mdd": mdd,
        "turnover": turnover,
        "hold_days": hold_days,
    }


def run_backtest(
    data: dict[str, pd.DataFrame],
    signal: pd.DataFrame,
    hold_days: int,
    fee_bps: float,
    slippage_bps: float,
    start_date: pd.Timestamp | None = None,
    end_date: pd.Timestamp | None = None,
) -> dict[str, Any]:
    close = data["close"]
    open_px = data.get("open", close)

    close = _slice_by_range(close, start_date, end_date)
    open_px = _slice_by_range(open_px, start_date, end_date)
    signal = _slice_by_range(signal, start_date, end_date).reindex_like(close).fillna(False)

    entry = open_px.shift(-1)
    exit_px = close.shift(-hold_days)
    valid = (entry > 0.0) & (exit_px > 0.0)

    gross = exit_px.where(valid) / entry.where(valid) - 1.0
    gross = gross.replace([np.inf, -np.inf], np.nan)

    round_trip_cost = (float(fee_bps) + float(slippage_bps)) * 2.0 / 10000.0
    net = gross - round_trip_cost

    selected_returns = net.where(signal & valid)
    return _summarize(selected_returns=selected_returns, hold_days=hold_days)
