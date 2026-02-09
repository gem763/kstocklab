from __future__ import annotations

from typing import Any


def compute_oos_score(summary: dict[str, Any], scoring_cfg: dict[str, Any] | None = None) -> float:
    cfg = scoring_cfg or {}
    oos_sharpe = float(summary.get("oos_sharpe", 0.0))
    oos_avg_return = float(summary.get("oos_avg_return", 0.0))
    oos_consistency = float(summary.get("oos_consistency", 0.0))
    oos_mdd = float(summary.get("oos_mdd", 0.0))
    short_long_return_gap = abs(float(summary.get("oos_short_long_return_gap", 0.0)))
    split_avg_return_std = float(summary.get("oos_split_avg_return_std", 0.0))
    patience_run_ratio = float(summary.get("oos_patience_run_ratio", 0.0))
    ewma_return = float(summary.get("oos_ewma_return", 0.0))
    short_long_hit_gap = float(summary.get("oos_short_long_hit_gap", 0.0))

    # OOS-first scoring:
    # - reward sharpe and consistency
    # - reward average trade return
    # - penalize deep drawdown
    # - penalize regime instability (short/long gap, split std, patience run)
    # - reward improving short-term momentum via EWMA
    score = (
        float(cfg.get("weight_oos_sharpe", 0.55)) * oos_sharpe
        + float(cfg.get("weight_oos_avg_return", 40.0)) * oos_avg_return
        + float(cfg.get("weight_oos_consistency", 0.35)) * oos_consistency
        - float(cfg.get("weight_oos_mdd_penalty", 0.25)) * abs(min(oos_mdd, 0.0))
        - float(cfg.get("weight_short_long_gap_penalty", 18.0)) * short_long_return_gap
        - float(cfg.get("weight_split_std_penalty", 10.0)) * split_avg_return_std
        - float(cfg.get("weight_patience_run_penalty", 0.35)) * patience_run_ratio
        + float(cfg.get("weight_ewma_return_bonus", 10.0)) * max(ewma_return, 0.0)
        + float(cfg.get("weight_short_long_hit_gap", 0.10)) * short_long_hit_gap
    )
    return float(score)
