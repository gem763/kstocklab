from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any

import pandas as pd


LEDGER_COLUMNS = [
    "date",
    "pattern_id",
    "params",
    "train_range",
    "test_range",
    "sharpe",
    "cagr",
    "mdd",
    "turnover",
    "notes",
]


def _allocate_report_dir(output_root: str, run_date: str) -> Path:
    root = Path(output_root)
    base = root / run_date
    if not base.exists():
        return base

    suffix = 1
    while True:
        candidate = root / f"{run_date}-{suffix}"
        if not candidate.exists():
            return candidate
        suffix += 1


def _append_markdown(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    prev = path.read_text(encoding="utf-8") if path.exists() else ""
    if prev and not prev.endswith("\n"):
        prev += "\n"
    path.write_text(prev + "\n".join(lines) + "\n", encoding="utf-8")


def _append_ledger(ledger_path: str, top_df: pd.DataFrame, run_date: str) -> None:
    ledger = Path(ledger_path)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    if ledger.exists():
        old = pd.read_parquet(ledger)
    else:
        old = pd.DataFrame(columns=LEDGER_COLUMNS)
    if not old.empty and "date" in old.columns:
        normalized = pd.to_datetime(old["date"], errors="coerce").dt.date.astype(str)
        old = old[normalized != str(run_date)].copy()

    rows = []
    for _, row in top_df.iterrows():
        rows.append(
            {
                "date": run_date,
                "pattern_id": row["candidate_id"],
                "params": json.dumps(row["params"], ensure_ascii=False, sort_keys=True),
                "train_range": row.get("train_range", ""),
                "test_range": row.get("test_range", ""),
                "sharpe": float(row.get("oos_sharpe", 0.0)),
                "cagr": float(row.get("oos_cagr", 0.0)),
                "mdd": float(row.get("oos_mdd", 0.0)),
                "turnover": float(row.get("oos_turnover", 0.0)),
                "notes": f"score={float(row.get('score', 0.0)):.6f}",
            }
        )
    new_rows = pd.DataFrame(rows, columns=LEDGER_COLUMNS)
    out = pd.concat([old, new_rows], ignore_index=True)
    if not out.empty:
        out = out.drop_duplicates(
            subset=["date", "pattern_id", "train_range", "test_range"], keep="last"
        ).reset_index(drop=True)
    out.to_parquet(ledger, index=False)


def write_outputs(
    output_root: str,
    mode: str,
    dataset_meta: dict[str, Any],
    stage1_df: pd.DataFrame,
    final_df: pd.DataFrame,
    top_df: pd.DataFrame,
    literature_ctx: dict[str, Any],
    config_path: str,
    memory_cfg: dict[str, Any],
    run_control: dict[str, Any],
) -> Path:
    run_date = date.today().isoformat()
    report_dir = _allocate_report_dir(output_root=output_root, run_date=run_date)
    report_dir.mkdir(parents=True, exist_ok=True)
    tables_dir = report_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    stage1_out = stage1_df.copy()
    final_out = final_df.copy()
    top_out = top_df.copy()
    for df in (stage1_out, final_out, top_out):
        if "params" in df.columns:
            df["params"] = df["params"].apply(lambda x: json.dumps(x, ensure_ascii=False, sort_keys=True))
    stage1_out.to_csv(tables_dir / "stage1_candidates.csv", index=False)
    final_out.to_csv(tables_dir / "final_candidates.csv", index=False)
    top_out.to_csv(tables_dir / "top_candidates.csv", index=False)

    top_lines = []
    for _, row in top_df.iterrows():
        top_lines.append(
            (
                f"- `{row['candidate_id']}` | score={float(row['score']):.4f} | "
                f"oos_sharpe={float(row['oos_sharpe']):.4f} | "
                f"oos_cagr={float(row['oos_cagr']):.4f} | "
                f"oos_mdd={float(row['oos_mdd']):.4f} | "
                f"short_long_gap={float(row.get('oos_short_long_return_gap', 0.0)):.4f} | "
                f"split_std={float(row.get('oos_split_avg_return_std', 0.0)):.4f} | "
                f"patience_run={int(row.get('oos_patience_run', 0))}"
            )
        )
    if not top_lines:
        top_lines = ["- 검증을 통과한 후보가 없습니다."]

    static_info = literature_ctx.get("static", {})
    cache_info = literature_ctx.get("cache", {})
    curated_summary = literature_ctx.get("curated_summary", {})
    recent_sources = literature_ctx.get("recent_sources", [])
    warnings = literature_ctx.get("warnings", [])
    if run_control.get("deadline_hit"):
        warnings.append("시간 예산에 도달하여 실행이 조기 종료되었습니다. 일부 후보는 미평가 상태일 수 있습니다.")

    summary_path = report_dir / "summary.md"
    lines = [
        f"# 일일 패턴 연구 요약 ({run_date})",
        "",
        "## 실행 설정",
        f"- 모드: `{mode}`",
        f"- 설정 파일: `{config_path}`",
        f"- 데이터 행 수: `{dataset_meta['rows']}`",
        f"- 종목 수: `{dataset_meta['tickers']}`",
        f"- 데이터 기간: `{dataset_meta['start_date']}..{dataset_meta['end_date']}`",
        f"- 로드 필드: `{', '.join(dataset_meta['fields'])}`",
        f"- 시장지수 상태: `{dataset_meta.get('market_index_status', '')}`",
        f"- 시장지수 컬럼: `{dataset_meta.get('market_index_column', '')}`",
        f"- 1단계 후보 수: `{len(stage1_df)}`",
        f"- 최종 검증 후보 수: `{len(final_df)}`",
        f"- 시간 예산(분): `{run_control.get('max_minutes')}`",
        f"- 실제 소요 시간(분): `{float(run_control.get('elapsed_minutes', 0.0)):.2f}`",
        "",
        "## 실행 제어",
        f"- 1단계 계획/평가: `{run_control['stage1']['planned']}/{run_control['stage1']['evaluated']}`",
        f"- 2단계 계획/평가: `{run_control['stage2']['planned']}/{run_control['stage2']['evaluated']}`",
        f"- 시간 예산 도달 여부: `{run_control.get('deadline_hit')}`",
        "",
        "## 레거시 참고자료 (정적 PDF)",
        f"- 파일 경로: `{static_info.get('pdf_path', '')}`",
        f"- 상태: `{static_info.get('status', '')}`",
        f"- 스캔 페이지: `{static_info.get('scanned_pages', 0)}` / `{static_info.get('total_pages', 0)}`",
        f"- 추출 글자 수: `{static_info.get('extracted_chars', 0)}`",
        f"- 캐시 사용 여부: `{cache_info.get('used')}`",
        f"- 캐시 상태: `{cache_info.get('status', '')}`",
        f"- 캐시 경로: `{cache_info.get('path', '')}`",
        f"- 요약 파일: `{curated_summary.get('path', '')}`",
        f"- 요약 파일 존재: `{curated_summary.get('exists')}`",
        "",
        "## 최신 참고문헌",
    ]

    if recent_sources:
        for src in recent_sources:
            title = src.get("title", "")
            year = src.get("year", "")
            url = src.get("url", "")
            note = src.get("note", "")
            lines.append(f"- {title} ({year}) - {url} - {note}")
    else:
        lines.append("- `configs/recent_sources.yaml`에 등록된 최신 참고문헌이 없습니다.")

    lines.extend(
        [
            "",
            "## 경고/주의사항",
        ]
    )
    for w in warnings:
        lines.append(f"- {w}")

    lines.extend(
        [
            "",
            "## 상위 패턴",
            *top_lines,
            "",
            "## 재현 방법",
            f"- 실행 명령: `python -m research.run --config {config_path}`",
            f"- 결과 테이블: `{tables_dir / 'stage1_candidates.csv'}`",
            f"- 결과 테이블: `{tables_dir / 'final_candidates.csv'}`",
            f"- 결과 테이블: `{tables_dir / 'top_candidates.csv'}`",
        ]
    )
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    _append_ledger(memory_cfg["ledger_path"], top_df=top_df, run_date=run_date)

    backlog_lines = [f"## {run_date} ({mode})", "후속 검증 후보:"]
    for _, row in top_df.head(5).iterrows():
        backlog_lines.append(
            (
                f"- {row['candidate_id']} -> 인접 파라미터 검증: {json.dumps(row['params'], ensure_ascii=False)} "
                f"(short_long_gap={float(row.get('oos_short_long_return_gap', 0.0)):.4f}, "
                f"patience_run={int(row.get('oos_patience_run', 0))})"
            )
        )
    if len(top_df) == 0:
        backlog_lines.append("- 유효 후보가 없습니다. 가설 공간을 넓히고 비용 가정을 다시 점검하세요.")
    _append_markdown(Path(memory_cfg["backlog_path"]), backlog_lines + [""])

    lesson_lines = [f"## {run_date} ({mode})"]
    if len(top_df) > 0:
        best = top_df.iloc[0]
        lesson_lines.append(
            f"- 현재 OOS 기준 최상위 후보: {best['candidate_id']} (score={float(best['score']):.4f})"
        )
    lesson_lines.extend(
        [
            "- 레거시 패턴 주장은 가설로 취급하고 OOS 분할로 재검증했다.",
            "- 단기/장기 OOS 통계와 EWMA를 비교하고 인내구간(연속 부진 구간)을 함께 점검했다.",
            "- 최신 참고문헌을 보강하며 레짐 변화(regime drift)를 지속 모니터링한다.",
            "",
        ]
    )
    _append_markdown(Path(memory_cfg["lessons_path"]), lesson_lines)
    return summary_path
