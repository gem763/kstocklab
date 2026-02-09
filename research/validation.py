from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .backtest import run_backtest
from .eval import compute_oos_score
from .signals.registry import PatternCandidate, generate_candidate_signal


@dataclass(frozen=True)
class WalkForwardSplit:
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp

    @property
    def train_range(self) -> str:
        return f"{self.train_start.date().isoformat()}..{self.train_end.date().isoformat()}"

    @property
    def test_range(self) -> str:
        return f"{self.test_start.date().isoformat()}..{self.test_end.date().isoformat()}"


def make_walkforward_splits(
    index: pd.DatetimeIndex, train_years: int, test_years: int, step_years: int
) -> list[WalkForwardSplit]:
    idx = pd.DatetimeIndex(index).sort_values().unique()
    if idx.empty:
        return []

    first_date = idx.min()
    last_date = idx.max()
    anchor = first_date + pd.DateOffset(years=train_years)
    splits: list[WalkForwardSplit] = []

    while anchor + pd.DateOffset(years=test_years) <= last_date:
        train_start = anchor - pd.DateOffset(years=train_years)
        train_end = anchor - pd.Timedelta(days=1)
        test_start = anchor
        test_end = anchor + pd.DateOffset(years=test_years) - pd.Timedelta(days=1)

        train_mask = (idx >= train_start) & (idx <= train_end)
        test_mask = (idx >= test_start) & (idx <= test_end)
        if train_mask.sum() >= 252 and test_mask.sum() >= 120:
            splits.append(
                WalkForwardSplit(
                    train_start=pd.Timestamp(train_start),
                    train_end=pd.Timestamp(train_end),
                    test_start=pd.Timestamp(test_start),
                    test_end=pd.Timestamp(test_end),
                )
            )

        anchor = anchor + pd.DateOffset(years=step_years)
    return splits


def _mean_metric(metrics: list[dict[str, Any]], key: str) -> float:
    if not metrics:
        return 0.0
    return float(sum(float(m.get(key, 0.0)) for m in metrics) / len(metrics))


def _max_consecutive_non_positive(values: list[float]) -> int:
    max_run = 0
    run = 0
    for v in values:
        if v <= 0.0:
            run += 1
            if run > max_run:
                max_run = run
        else:
            run = 0
    return int(max_run)


def _compute_regime_stability_metrics(
    test_metrics: list[dict[str, Any]],
    stability_cfg: dict[str, Any] | None,
) -> dict[str, Any]:
    if not test_metrics:
        return {
            "oos_short_avg_return": 0.0,
            "oos_long_avg_return": 0.0,
            "oos_short_hit_rate": 0.0,
            "oos_long_hit_rate": 0.0,
            "oos_short_long_return_gap": 0.0,
            "oos_short_long_hit_gap": 0.0,
            "oos_split_avg_return_std": 0.0,
            "oos_split_hit_rate_std": 0.0,
            "oos_patience_run": 0,
            "oos_patience_run_ratio": 0.0,
            "oos_ewma_return": 0.0,
            "oos_split_mdd": 0.0,
        }

    cfg = stability_cfg or {}
    returns = pd.Series([float(x.get("avg_return", 0.0)) for x in test_metrics], dtype="float64")
    hit_rates = pd.Series([float(x.get("hit_rate", 0.0)) for x in test_metrics], dtype="float64")
    n_splits = max(len(returns), 1)

    short_window = int(cfg.get("short_window_splits", 3))
    short_window = max(1, min(short_window, n_splits))
    ewma_span = int(cfg.get("ewma_span_splits", short_window))
    ewma_span = max(1, min(ewma_span, n_splits))

    short_avg_return = float(returns.tail(short_window).mean())
    long_avg_return = float(returns.mean())
    short_hit_rate = float(hit_rates.tail(short_window).mean())
    long_hit_rate = float(hit_rates.mean())

    split_return_std = float(returns.std(ddof=1)) if n_splits > 1 else 0.0
    split_hit_std = float(hit_rates.std(ddof=1)) if n_splits > 1 else 0.0

    patience_run = _max_consecutive_non_positive(returns.tolist())
    patience_run_ratio = float(patience_run / n_splits)

    ewma_return = float(returns.ewm(span=ewma_span, adjust=False).mean().iloc[-1])
    split_equity = (1.0 + returns.fillna(0.0)).cumprod()
    split_mdd = float((split_equity / split_equity.cummax() - 1.0).min()) if not split_equity.empty else 0.0

    return {
        "oos_short_avg_return": short_avg_return,
        "oos_long_avg_return": long_avg_return,
        "oos_short_hit_rate": short_hit_rate,
        "oos_long_hit_rate": long_hit_rate,
        "oos_short_long_return_gap": short_avg_return - long_avg_return,
        "oos_short_long_hit_gap": short_hit_rate - long_hit_rate,
        "oos_split_avg_return_std": split_return_std,
        "oos_split_hit_rate_std": split_hit_std,
        "oos_patience_run": int(patience_run),
        "oos_patience_run_ratio": patience_run_ratio,
        "oos_ewma_return": ewma_return,
        "oos_split_mdd": split_mdd,
    }


def _market_filter_mask(
    index: pd.DatetimeIndex,
    columns: pd.Index,
    market_index: pd.Series,
    cfg: dict[str, Any],
) -> pd.DataFrame:
    filter_type = str(cfg.get("type", "above_ma"))
    if filter_type == "momentum":
        lookback = int(cfg.get("lookback", 63))
        threshold = float(cfg.get("threshold", 0.0))
        regime = market_index / market_index.shift(lookback) - 1.0 > threshold
    else:
        ma_window = int(cfg.get("ma_window", 120))
        regime = market_index > market_index.rolling(ma_window).mean()

    regime = regime.reindex(index).fillna(False)
    mask = pd.DataFrame({col: regime for col in columns}, index=index)
    return mask


def _apply_market_filter(
    signal: pd.DataFrame, data: dict[str, Any], market_filter_cfg: dict[str, Any] | None
) -> tuple[pd.DataFrame, str]:
    if not market_filter_cfg or not bool(market_filter_cfg.get("enabled", False)):
        return signal, "disabled"

    market_index = data.get("market_index")
    if market_index is None or not isinstance(market_index, pd.Series):
        return signal, "enabled_but_missing_market_index"

    mask = _market_filter_mask(
        index=signal.index,
        columns=signal.columns,
        market_index=pd.to_numeric(market_index, errors="coerce"),
        cfg=market_filter_cfg,
    )
    return (signal & mask).fillna(False), "applied"


def evaluate_candidate_on_splits(
    candidate: PatternCandidate,
    data: dict[str, Any],
    splits: list[WalkForwardSplit],
    fee_bps: float,
    slippage_bps: float,
    market_filter_cfg: dict[str, Any] | None = None,
    stability_cfg: dict[str, Any] | None = None,
    scoring_cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    signal = generate_candidate_signal(candidate=candidate, data=data)
    signal, market_filter_status = _apply_market_filter(signal, data, market_filter_cfg)
    per_split: list[dict[str, Any]] = []

    for split in splits:
        train_metrics = run_backtest(
            data=data,
            signal=signal,
            hold_days=candidate.hold_days,
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
            start_date=split.train_start,
            end_date=split.train_end,
        )
        test_metrics = run_backtest(
            data=data,
            signal=signal,
            hold_days=candidate.hold_days,
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
            start_date=split.test_start,
            end_date=split.test_end,
        )
        per_split.append(
            {
                "train": train_metrics,
                "test": test_metrics,
                "train_range": split.train_range,
                "test_range": split.test_range,
            }
        )

    train_metrics = [x["train"] for x in per_split]
    test_metrics = [x["test"] for x in per_split]
    oos_consistency = (
        float(sum(1 for m in test_metrics if float(m.get("avg_return", 0.0)) > 0.0) / len(test_metrics))
        if test_metrics
        else 0.0
    )
    regime_metrics = _compute_regime_stability_metrics(
        test_metrics=test_metrics,
        stability_cfg=stability_cfg,
    )

    summary = {
        "candidate_id": candidate.candidate_id,
        "pattern_name": candidate.name,
        "description": candidate.description,
        "params": candidate.params,
        "hold_days": candidate.hold_days,
        "split_count": len(per_split),
        "train_sharpe": _mean_metric(train_metrics, "sharpe"),
        "train_cagr": _mean_metric(train_metrics, "cagr"),
        "train_mdd": _mean_metric(train_metrics, "mdd"),
        "oos_sharpe": _mean_metric(test_metrics, "sharpe"),
        "oos_cagr": _mean_metric(test_metrics, "cagr"),
        "oos_mdd": _mean_metric(test_metrics, "mdd"),
        "oos_avg_return": _mean_metric(test_metrics, "avg_return"),
        "oos_hit_rate": _mean_metric(test_metrics, "hit_rate"),
        "oos_turnover": _mean_metric(test_metrics, "turnover"),
        "oos_num_trades": _mean_metric(test_metrics, "num_trades"),
        "oos_consistency": oos_consistency,
        "train_range": per_split[0]["train_range"] if per_split else "",
        "test_range": per_split[-1]["test_range"] if per_split else "",
        "market_filter_status": market_filter_status,
        **regime_metrics,
    }
    summary["score"] = compute_oos_score(summary, scoring_cfg=scoring_cfg)
    return summary
