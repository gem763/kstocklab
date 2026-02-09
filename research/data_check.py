#!/usr/bin/env python3
"""Quick parquet sanity check."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def infer_dates(df: pd.DataFrame) -> pd.Series:
    if isinstance(df.index, pd.MultiIndex):
        if "date" in df.index.names:
            return pd.to_datetime(df.index.get_level_values("date"), errors="coerce")
        return pd.to_datetime(df.index.get_level_values(0), errors="coerce")

    if isinstance(df.index, pd.DatetimeIndex):
        return pd.to_datetime(df.index, errors="coerce")

    if "date" in df.columns:
        return pd.to_datetime(df["date"], errors="coerce")

    return pd.Series([], dtype="datetime64[ns]")


def infer_stock_count(df: pd.DataFrame) -> int:
    if "ticker" in df.columns:
        return int(df["ticker"].nunique(dropna=True))

    if isinstance(df.index, pd.MultiIndex) and "ticker" in df.index.names:
        tickers = pd.Index(df.index.get_level_values("ticker"))
        return int(tickers.nunique(dropna=True))

    # Wide format default: one ticker per column.
    return int(df.shape[1])


def main() -> None:
    parser = argparse.ArgumentParser(description="Check parquet schema quickly.")
    parser.add_argument(
        "parquet_path",
        nargs="?",
        default="data/close.parquet",
        help="Parquet file path (default: data/close.parquet)",
    )
    args = parser.parse_args()

    parquet_path = Path(args.parquet_path)
    if not parquet_path.exists():
        raise FileNotFoundError(f"Parquet not found: {parquet_path}")

    df = pd.read_parquet(parquet_path)

    dates = pd.Series(infer_dates(df)).dropna()
    if dates.empty:
        latest_5_text = "(date 정보 없음)"
    else:
        latest_5 = sorted(dates.dt.normalize().unique(), reverse=True)[:5]
        latest_5_text = ", ".join(d.strftime("%Y-%m-%d") for d in latest_5)

    print(f"파일: {parquet_path}")
    print(f"최근 날짜 5개: {latest_5_text}")
    print(f"종목 수: {infer_stock_count(df)}")
    print(f"컬럼명: {list(df.columns)}")


if __name__ == "__main__":
    main()
