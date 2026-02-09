from __future__ import annotations

import argparse
import random
from pathlib import Path
import time
from typing import Any

import numpy as np
import pandas as pd
import yaml

from .data import load_market_data
from .literature import collect_literature_context
from .report import write_outputs
from .signals.registry import PatternCandidate, build_candidates
from .validation import evaluate_candidate_on_splits, make_walkforward_splits


def load_config(path: str | Path) -> dict:
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Missing config file: {cfg_path}")
    with cfg_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)


def _to_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    return df.sort_values("score", ascending=False).reset_index(drop=True)


def _evaluate_stage(
    stage_name: str,
    candidates: list[PatternCandidate],
    data: dict[str, Any],
    splits: list,
    fee_bps: float,
    slippage_bps: float,
    market_filter_cfg: dict[str, Any] | None = None,
    stability_cfg: dict[str, Any] | None = None,
    scoring_cfg: dict[str, Any] | None = None,
    deadline: float | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    planned = len(candidates)
    print(f"[{stage_name}] evaluating {planned} candidates over {len(splits)} splits")
    rows: list[dict[str, Any]] = []
    timed_out = False

    for i, candidate in enumerate(candidates, start=1):
        if deadline is not None and time.monotonic() >= deadline:
            timed_out = True
            print(f"[{stage_name}] time budget reached. stopping early at {i - 1}/{planned}.")
            break

        print(f"[{stage_name}] {i}/{len(candidates)} {candidate.candidate_id}")
        result = evaluate_candidate_on_splits(
            candidate=candidate,
            data=data,
            splits=splits,
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
            market_filter_cfg=market_filter_cfg,
            stability_cfg=stability_cfg,
            scoring_cfg=scoring_cfg,
        )
        rows.append(result)

    meta = {
        "planned": planned,
        "evaluated": len(rows),
        "timed_out": timed_out,
        "splits": len(splits),
    }
    return _to_frame(rows), meta


def main() -> None:
    parser = argparse.ArgumentParser(description="Run research scaffold.")
    parser.add_argument("--config", required=True, help="Path to YAML config")
    args = parser.parse_args()

    cfg = load_config(args.config)
    _set_seed(int(cfg.get("seed", 42)))
    run_started = time.monotonic()

    data, dataset_meta = load_market_data(cfg["data"])
    research_cfg = cfg["research"]
    walk_cfg = research_cfg["walkforward"]
    splits = make_walkforward_splits(
        index=data["close"].index,
        train_years=int(walk_cfg["train_years"]),
        test_years=int(walk_cfg["test_years"]),
        step_years=int(walk_cfg["step_years"]),
    )
    if not splits:
        raise ValueError("No walk-forward split generated. Check date range and walkforward config.")

    candidates = build_candidates(research_cfg["patterns"])
    costs = research_cfg.get("costs", {})
    fee_bps = float(costs.get("fee_bps", 5.0))
    slippage_bps = float(costs.get("slippage_bps", 5.0))
    stability_cfg = research_cfg.get("stability", {})
    scoring_cfg = research_cfg.get("scoring", {})
    max_minutes = research_cfg.get("max_minutes")
    deadline: float | None = None
    if max_minutes is not None:
        deadline = run_started + float(max_minutes) * 60.0

    quick_n = int(research_cfg.get("quick_splits", 3))
    stage1_splits = splits[-quick_n:] if quick_n > 0 else splits
    stage1_df, stage1_meta = _evaluate_stage(
        stage_name="stage1",
        candidates=candidates,
        data=data,
        splits=stage1_splits,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
        market_filter_cfg=research_cfg.get("market_filter"),
        stability_cfg=stability_cfg,
        scoring_cfg=scoring_cfg,
        deadline=deadline,
    )

    stage1_top_k = int(research_cfg.get("stage1_top_k", 10))
    if stage1_df.empty or "candidate_id" not in stage1_df.columns:
        stage2_candidates = []
    else:
        top_candidate_ids = set(stage1_df.head(stage1_top_k)["candidate_id"].tolist())
        stage2_candidates = [c for c in candidates if c.candidate_id in top_candidate_ids]

    final_df, stage2_meta = _evaluate_stage(
        stage_name="stage2",
        candidates=stage2_candidates,
        data=data,
        splits=splits,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
        market_filter_cfg=research_cfg.get("market_filter"),
        stability_cfg=stability_cfg,
        scoring_cfg=scoring_cfg,
        deadline=deadline,
    )
    final_top_n = int(research_cfg.get("final_top_n", 5))
    top_df = final_df.head(final_top_n).copy()

    literature_ctx = collect_literature_context(cfg.get("literature", {}))
    run_control = {
        "max_minutes": float(max_minutes) if max_minutes is not None else None,
        "elapsed_minutes": (time.monotonic() - run_started) / 60.0,
        "deadline_hit": bool(stage1_meta.get("timed_out") or stage2_meta.get("timed_out")),
        "stage1": stage1_meta,
        "stage2": stage2_meta,
    }
    summary_path = write_outputs(
        output_root=cfg["report"]["output_root"],
        mode=cfg.get("mode", "daily"),
        dataset_meta=dataset_meta,
        stage1_df=stage1_df,
        final_df=final_df,
        top_df=top_df,
        literature_ctx=literature_ctx,
        config_path=args.config,
        memory_cfg=cfg["memory"],
        run_control=run_control,
    )
    print(f"summary: {summary_path}")
    if not top_df.empty:
        print("top_pattern:", top_df.iloc[0]["candidate_id"])


if __name__ == "__main__":
    main()
