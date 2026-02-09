# 일일 패턴 연구 요약 (2026-02-09)

## 실행 설정
- 모드: `smoke`
- 설정 파일: `configs/smoke.yaml`
- 데이터 행 수: `2452`
- 종목 수: `250`
- 데이터 기간: `2016-01-04..2025-12-30`
- 로드 필드: `amount, close, high, low, marketcap, open, volume`
- 시장지수 상태: `missing_file`
- 시장지수 컬럼: ``
- 1단계 후보 수: `2`
- 최종 검증 후보 수: `2`
- 시간 예산(분): `2.0`
- 실제 소요 시간(분): `0.19`

## 실행 제어
- 1단계 계획/평가: `2/2`
- 2단계 계획/평가: `2/2`
- 시간 예산 도달 여부: `False`

## 레거시 참고자료 (정적 PDF)
- 파일 경로: `static/패턴은 정말 존재하는가.pdf`
- 상태: `ok`
- 스캔 페이지: `8` / `97`
- 추출 글자 수: `8850`
- 캐시 사용 여부: `True`
- 캐시 상태: `cache_hit`
- 캐시 경로: `research/memory/legacy_book_cache.yaml`
- 요약 파일: `research/memory/legacy_book_summary.md`
- 요약 파일 존재: `True`

## 최신 참고문헌
- `configs/recent_sources.yaml`에 등록된 최신 참고문헌이 없습니다.

## 경고/주의사항
- 레거시 참고자료는 과거 시장 맥락 중심이므로 OOS 재검증이 필요합니다.

## 상위 패턴
- `donchian_volume_breakout|lookback=20,volume_mult=1.2,volume_window=20|hold=10` | score=0.2537 | oos_sharpe=0.9900 | oos_cagr=75.7755 | oos_mdd=-0.8154 | short_long_gap=-0.0059 | split_std=0.0138 | patience_run=1
- `ma_pullback|fast=20,pullback_pct=-0.04,slow=60|hold=5` | score=-1.1456 | oos_sharpe=-1.3128 | oos_cagr=-0.0961 | oos_mdd=-0.6595 | short_long_gap=-0.0004 | split_std=0.0060 | patience_run=2

## 재현 방법
- 실행 명령: `python -m research.run --config configs/smoke.yaml`
- 결과 테이블: `reports/2026-02-09-1/tables/stage1_candidates.csv`
- 결과 테이블: `reports/2026-02-09-1/tables/final_candidates.csv`
- 결과 테이블: `reports/2026-02-09-1/tables/top_candidates.csv`
