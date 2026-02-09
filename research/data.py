from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def _load_wide_parquet(path: str | Path) -> pd.DataFrame:
    parquet_path = Path(path)
    if not parquet_path.exists():
        raise FileNotFoundError(f"Missing parquet file: {parquet_path}")

    df = pd.read_parquet(parquet_path)
    if "date" in df.columns:
        raise ValueError(
            f"Expected wide parquet with date index, but got long-like columns in: {parquet_path}"
        )

    if not isinstance(df.index, pd.DatetimeIndex):
        idx = pd.to_datetime(df.index, errors="coerce")
        if idx.isna().all():
            raise ValueError(f"Could not parse datetime index from: {parquet_path}")
        df = df.copy()
        df.index = idx

    df = df[~df.index.duplicated(keep="first")].sort_index()
    df.columns = df.columns.astype(str)
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _clip_dates(df: pd.DataFrame, start_date: str | None, end_date: str | None) -> pd.DataFrame:
    out = df
    if start_date:
        out = out[out.index >= pd.Timestamp(start_date)]
    if end_date:
        out = out[out.index <= pd.Timestamp(end_date)]
    return out


def _apply_universe_filter(
    data: dict[str, pd.DataFrame],
    max_tickers: int | None,
    min_history_days: int,
    liquidity_field: str,
) -> dict[str, pd.DataFrame]:
    close = data["close"]
    valid_counts = close.notna().sum()
    keep = valid_counts[valid_counts >= min_history_days].index
    if keep.empty:
        raise ValueError("No ticker passes min_history_days filter.")

    if max_tickers and len(keep) > max_tickers:
        if liquidity_field in data:
            liquidity = data[liquidity_field][keep].replace(0.0, np.nan).median()
        else:
            liquidity = close[keep].replace(0.0, np.nan).median()
        keep = liquidity.sort_values(ascending=False).head(max_tickers).index

    return {name: df.loc[:, keep] for name, df in data.items()}


def _load_market_index_series(
    path: str | None,
    index: pd.DatetimeIndex,
    start_date: str | None,
    end_date: str | None,
    column: str | None,
) -> tuple[pd.Series | None, str, str]:
    if not path:
        return None, "", "not_configured"

    parquet_path = Path(path)
    if not parquet_path.exists():
        return None, "", "missing_file"

    df = _load_wide_parquet(path)
    df = _clip_dates(df, start_date=start_date, end_date=end_date)
    if df.empty:
        return None, "", "empty_after_date_clip"

    chosen_col = column if column else str(df.columns[0])
    if chosen_col not in df.columns:
        return None, chosen_col, "missing_column"

    series = pd.to_numeric(df[chosen_col], errors="coerce")
    series = series.reindex(index).ffill()
    return series, chosen_col, "ok"


def load_market_data(data_cfg: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    field_to_cfg_key = {
        "open": "open_path",
        "high": "high_path",
        "low": "low_path",
        "close": "close_path",
        "volume": "volume_path",
        "amount": "amount_path",
        "marketcap": "marketcap_path",
    }

    loaded: dict[str, pd.DataFrame] = {}
    for field, cfg_key in field_to_cfg_key.items():
        path = data_cfg.get(cfg_key)
        if path:
            loaded[field] = _load_wide_parquet(path)

    if "close" not in loaded:
        raise ValueError("close_path is required in config data section.")

    common_index = loaded["close"].index
    common_cols = loaded["close"].columns
    for df in loaded.values():
        common_index = common_index.intersection(df.index)
        common_cols = common_cols.intersection(df.columns)

    for name, df in loaded.items():
        aligned = df.loc[common_index, common_cols]
        aligned = _clip_dates(
            aligned,
            start_date=data_cfg.get("start_date"),
            end_date=data_cfg.get("end_date"),
        )
        loaded[name] = aligned

    loaded = _apply_universe_filter(
        loaded,
        max_tickers=data_cfg.get("max_tickers"),
        min_history_days=int(data_cfg.get("min_history_days", 252)),
        liquidity_field=str(data_cfg.get("liquidity_field", "amount")),
    )

    close = loaded["close"]
    market_index_series, market_index_column, market_index_status = _load_market_index_series(
        path=data_cfg.get("market_index_close_path"),
        index=close.index,
        start_date=data_cfg.get("start_date"),
        end_date=data_cfg.get("end_date"),
        column=data_cfg.get("market_index_column"),
    )

    data_out: dict[str, Any] = dict(loaded)
    if market_index_series is not None:
        data_out["market_index"] = market_index_series

    dataset_meta = {
        "rows": int(close.shape[0]),
        "tickers": int(close.shape[1]),
        "start_date": close.index.min().date().isoformat(),
        "end_date": close.index.max().date().isoformat(),
        "fields": sorted(loaded.keys()),
        "market_index_status": market_index_status,
        "market_index_column": market_index_column,
    }
    return data_out, dataset_meta
