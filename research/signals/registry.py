from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any, Callable

import pandas as pd

from .bb_width_breakout import generate_signal as bb_width_breakout
from .donchian_volume_breakout import generate_signal as donchian_volume_breakout
from .ma_pullback import generate_signal as ma_pullback
from .short_term_reversal import generate_signal as short_term_reversal

SignalFunc = Callable[[dict[str, pd.DataFrame], dict[str, Any]], pd.DataFrame]


@dataclass(frozen=True)
class PatternCandidate:
    name: str
    description: str
    params: dict[str, Any]
    hold_days: int
    candidate_id: str


REGISTRY: dict[str, SignalFunc] = {
    "bb_width_breakout": bb_width_breakout,
    "ma_pullback": ma_pullback,
    "donchian_volume_breakout": donchian_volume_breakout,
    "short_term_reversal": short_term_reversal,
}


def _to_iterable(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return [value]


def _format_candidate_id(name: str, params: dict[str, Any], hold_days: int) -> str:
    keys = sorted(params.keys())
    param_text = ",".join(f"{k}={params[k]}" for k in keys)
    return f"{name}|{param_text}|hold={hold_days}"


def build_candidates(pattern_specs: list[dict[str, Any]]) -> list[PatternCandidate]:
    candidates: list[PatternCandidate] = []
    for spec in pattern_specs:
        name = str(spec["name"])
        if name not in REGISTRY:
            raise ValueError(f"Unknown pattern in config: {name}")

        description = str(spec.get("description", name))
        param_grid = spec.get("params", {})
        if not param_grid:
            param_grid = {"hold_days": [5]}

        keys = sorted(param_grid.keys())
        values = [_to_iterable(param_grid[k]) for k in keys]
        for combo in product(*values):
            raw = dict(zip(keys, combo))
            hold_days = int(raw.pop("hold_days", 5))
            params = {k: raw[k] for k in sorted(raw.keys())}
            cid = _format_candidate_id(name=name, params=params, hold_days=hold_days)
            candidates.append(
                PatternCandidate(
                    name=name,
                    description=description,
                    params=params,
                    hold_days=hold_days,
                    candidate_id=cid,
                )
            )
    return candidates


def generate_candidate_signal(
    candidate: PatternCandidate, data: dict[str, pd.DataFrame]
) -> pd.DataFrame:
    func = REGISTRY[candidate.name]
    return func(data, candidate.params)

