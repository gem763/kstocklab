from __future__ import annotations

from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any

import yaml


def _to_iso_utc(timestamp: float | None) -> str:
    if timestamp is None:
        return ""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _extract_key_insights(text: str, max_items: int = 30) -> list[str]:
    insights: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        body = line[2:].strip()
        if len(body) < 8:
            continue
        insights.append(body)
        if len(insights) >= max_items:
            break
    return insights


def scan_static_pdf(pdf_path: str, max_pages: int, max_chars: int) -> dict[str, Any]:
    path = Path(pdf_path)
    result: dict[str, Any] = {
        "pdf_path": str(path),
        "exists": path.exists(),
        "status": "missing_file",
        "total_pages": 0,
        "scanned_pages": 0,
        "extracted_chars": 0,
        "excerpt": "",
    }
    if not path.exists():
        return result

    try:
        from pypdf import PdfReader
    except Exception:
        result["status"] = "missing_pypdf"
        return result

    logging.getLogger("pypdf").setLevel(logging.ERROR)
    try:
        reader = PdfReader(str(path))
    except Exception as exc:
        result["status"] = f"pdf_read_error:{exc.__class__.__name__}"
        return result
    total_pages = len(reader.pages)
    scan_pages = min(total_pages, max(1, int(max_pages)))
    chunks: list[str] = []
    for i in range(scan_pages):
        text = reader.pages[i].extract_text() or ""
        text = " ".join(text.split())
        if text:
            chunks.append(text)

    joined = "\n".join(chunks)
    excerpt = joined[: max(0, int(max_chars))]
    result.update(
        {
            "status": "ok",
            "total_pages": total_pages,
            "scanned_pages": scan_pages,
            "extracted_chars": len(joined),
            "excerpt": excerpt,
        }
    )
    return result


def _read_cache(cache_path: Path) -> dict[str, Any] | None:
    if not cache_path.exists():
        return None
    try:
        payload = yaml.safe_load(cache_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return None
    static = payload.get("static")
    if not isinstance(static, dict):
        return None
    return payload


def _write_cache(cache_path: Path, static_result: dict[str, Any], curated_summary: dict[str, Any]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cached_summary = {
        "path": curated_summary.get("path", ""),
        "exists": bool(curated_summary.get("exists", False)),
        "chars": int(curated_summary.get("chars", 0)),
        "mtime_utc": curated_summary.get("mtime_utc", ""),
        "key_insights": list(curated_summary.get("key_insights", [])),
        "content": curated_summary.get("text", ""),
    }
    payload = {
        "saved_at_utc": datetime.now(timezone.utc).isoformat(),
        "static": static_result,
        "curated_summary": cached_summary,
    }
    cache_path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def load_recent_sources(path: str | None) -> list[dict[str, str]]:
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        return []
    with p.open("r", encoding="utf-8") as f:
        payload = yaml.safe_load(f) or {}
    sources = payload.get("sources", [])
    cleaned: list[dict[str, str]] = []
    for row in sources:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title", "")).strip()
        year = str(row.get("year", "")).strip()
        url = str(row.get("url", "")).strip()
        note = str(row.get("note", "")).strip()
        if title or url:
            cleaned.append({"title": title, "year": year, "url": url, "note": note})
    return cleaned


def load_curated_summary(path: str | None) -> dict[str, Any]:
    if not path:
        return {
            "path": "",
            "exists": False,
            "text": "",
            "chars": 0,
            "mtime_utc": "",
            "key_insights": [],
        }
    p = Path(path)
    if not p.exists():
        return {
            "path": str(p),
            "exists": False,
            "text": "",
            "chars": 0,
            "mtime_utc": "",
            "key_insights": [],
        }
    text = p.read_text(encoding="utf-8")
    return {
        "path": str(p),
        "exists": True,
        "text": text,
        "chars": len(text),
        "mtime_utc": _to_iso_utc(p.stat().st_mtime),
        "key_insights": _extract_key_insights(text),
    }


def collect_literature_context(cfg: dict[str, Any]) -> dict[str, Any]:
    static_pdf = str(cfg.get("static_pdf", ""))
    max_pages = int(cfg.get("max_pages", 10))
    max_chars = int(cfg.get("max_chars", 4000))
    cache_path_raw = cfg.get("cache_path")
    use_cache = bool(cfg.get("use_cache", True))
    refresh_cache = bool(cfg.get("refresh_cache", False))
    curated_summary_path = cfg.get("summary_path")
    recent_sources_path = cfg.get("recent_sources_path")
    require_recent_evidence = bool(cfg.get("require_recent_evidence", False))
    curated_summary = load_curated_summary(curated_summary_path)

    cache = {
        "used": False,
        "path": str(cache_path_raw) if cache_path_raw else "",
        "status": "disabled",
        "saved_at_utc": "",
    }
    static_result: dict[str, Any]
    if cache_path_raw and use_cache:
        cache_path = Path(str(cache_path_raw))
        if not refresh_cache:
            cached = _read_cache(cache_path)
            if cached:
                static_result = dict(cached.get("static", {}))
                cache["used"] = True
                cache["status"] = "cache_hit"
                cache["saved_at_utc"] = str(cached.get("saved_at_utc", ""))
                cached_summary = cached.get("curated_summary", {})
                cached_summary_text = ""
                if isinstance(cached_summary, dict):
                    cached_summary_text = str(cached_summary.get("content", ""))
                if curated_summary.get("exists") and curated_summary.get("text", "") != cached_summary_text:
                    _write_cache(cache_path, static_result, curated_summary)
                    cache["status"] = "cache_hit_summary_synced"
                elif (not curated_summary.get("exists")) and isinstance(cached_summary, dict):
                    cached_text = str(cached_summary.get("content", ""))
                    if cached_text:
                        curated_summary = {
                            "path": str(cached_summary.get("path", curated_summary.get("path", ""))),
                            "exists": True,
                            "text": cached_text,
                            "chars": int(cached_summary.get("chars", len(cached_text))),
                            "mtime_utc": str(cached_summary.get("mtime_utc", "")),
                            "key_insights": list(cached_summary.get("key_insights", [])),
                        }
            else:
                static_result = scan_static_pdf(pdf_path=static_pdf, max_pages=max_pages, max_chars=max_chars)
                _write_cache(cache_path, static_result, curated_summary)
                cache["status"] = "cache_miss_saved"
        else:
            static_result = scan_static_pdf(pdf_path=static_pdf, max_pages=max_pages, max_chars=max_chars)
            _write_cache(cache_path, static_result, curated_summary)
            cache["status"] = "cache_refreshed"
    else:
        static_result = scan_static_pdf(pdf_path=static_pdf, max_pages=max_pages, max_chars=max_chars)

    recent_sources = load_recent_sources(recent_sources_path)

    warnings: list[str] = []
    warnings.append("레거시 참고자료는 과거 시장 맥락 중심이므로 OOS 재검증이 필요합니다.")
    if not curated_summary.get("exists"):
        warnings.append("정리된 레거시 요약이 없습니다. research/memory/legacy_book_summary.md를 확인하세요.")
    if require_recent_evidence and not recent_sources:
        warnings.append(
            "최신 근거 목록이 비어 있습니다. configs/recent_sources.yaml에 최신 논문/자료를 추가하세요."
        )

    return {
        "static": static_result,
        "cache": cache,
        "curated_summary": curated_summary,
        "recent_sources": recent_sources,
        "warnings": warnings,
    }
