#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import pandas as pd


PYKRX_INDEX_MAP = {
    "KOSPI": "1001",
    "KOSDAQ": "2001",
    "KOSPI200": "1028",
}

FDR_INDEX_MAP = {
    "KOSPI": "KS11",
    "KOSDAQ": "KQ11",
    "KOSPI200": "KS200",
}


def _fetch_with_pykrx(start: str, end: str, indices: list[str]) -> pd.DataFrame:
    try:
        from pykrx import stock
    except Exception as exc:
        raise RuntimeError("pykrx is not installed. run: pip install -r requirements-market.txt") from exc

    rows = {}
    start_key = start.replace("-", "")
    end_key = end.replace("-", "")
    for name in indices:
        ticker = PYKRX_INDEX_MAP.get(name)
        if not ticker:
            continue
        df = stock.get_index_ohlcv_by_date(start_key, end_key, ticker)
        if "종가" not in df.columns:
            continue
        s = pd.to_numeric(df["종가"], errors="coerce")
        s.index = pd.to_datetime(s.index, errors="coerce")
        rows[name] = s

    if not rows:
        raise RuntimeError("No index series fetched from pykrx.")

    out = pd.DataFrame(rows).sort_index()
    out = out[~out.index.duplicated(keep="first")]
    return out


def _fetch_with_fdr(start: str, end: str, indices: list[str]) -> pd.DataFrame:
    try:
        import FinanceDataReader as fdr
    except Exception as exc:
        raise RuntimeError(
            "FinanceDataReader is not installed. run: pip install -r requirements-market.txt"
        ) from exc

    rows = {}
    for name in indices:
        symbol = FDR_INDEX_MAP.get(name)
        if not symbol:
            continue
        df = fdr.DataReader(symbol, start, end)
        if "Close" not in df.columns:
            continue
        s = pd.to_numeric(df["Close"], errors="coerce")
        s.index = pd.to_datetime(s.index, errors="coerce")
        rows[name] = s

    if not rows:
        raise RuntimeError("No index series fetched from FinanceDataReader.")

    out = pd.DataFrame(rows).sort_index()
    out = out[~out.index.duplicated(keep="first")]
    return out


def fetch_market_index(provider: str, start: str, end: str, indices: list[str]) -> pd.DataFrame:
    if provider == "pykrx":
        return _fetch_with_pykrx(start=start, end=end, indices=indices)
    if provider == "fdr":
        return _fetch_with_fdr(start=start, end=end, indices=indices)
    raise ValueError(f"Unknown provider: {provider}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch market index close data and save as parquet.")
    parser.add_argument("--provider", choices=["pykrx", "fdr"], default="pykrx")
    parser.add_argument("--start", default="2000-01-01")
    parser.add_argument("--end", default=date.today().isoformat())
    parser.add_argument("--indices", default="KOSPI,KOSDAQ,KOSPI200")
    parser.add_argument("--out", default="data/market_index_close.parquet")
    args = parser.parse_args()

    indices = [x.strip().upper() for x in args.indices.split(",") if x.strip()]
    if not indices:
        raise ValueError("No indices provided.")

    out = fetch_market_index(provider=args.provider, start=args.start, end=args.end, indices=indices)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(out_path)

    print(f"saved: {out_path}")
    print(f"rows={len(out)}, columns={list(out.columns)}")
    print(f"date_range={out.index.min().date().isoformat()}..{out.index.max().date().isoformat()}")


if __name__ == "__main__":
    main()

