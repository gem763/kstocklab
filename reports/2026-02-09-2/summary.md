# 일일 패턴 연구 요약 (2026-02-09)

## 실행 설정
- 모드: `daily`
- 설정 파일: `configs/daily.yaml`
- 데이터 행 수: `6409`
- 종목 수: `800`
- 데이터 기간: `2000-01-04..2025-12-30`
- 로드 필드: `amount, close, high, low, marketcap, open, volume`
- 시장지수 상태: `missing_file`
- 시장지수 컬럼: ``
- 1단계 후보 수: `60`
- 최종 검증 후보 수: `10`
- 시간 예산(분): `8.0`
- 실제 소요 시간(분): `4.44`

## 실행 제어
- 1단계 계획/평가: `60/60`
- 2단계 계획/평가: `10/10`
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
- 최신 근거 목록이 비어 있습니다. configs/recent_sources.yaml에 최신 논문/자료를 추가하세요.

## 상위 패턴
- `ma_pullback|fast=10,pullback_pct=-0.03,slow=120|hold=10` | score=0.0663 | oos_sharpe=0.3526 | oos_cagr=1.3944 | oos_mdd=-0.8960 | short_long_gap=-0.0037 | split_std=0.0051 | patience_run=3
- `ma_pullback|fast=10,pullback_pct=-0.04,slow=120|hold=10` | score=0.0133 | oos_sharpe=0.2543 | oos_cagr=1.0900 | oos_mdd=-0.9059 | short_long_gap=-0.0035 | split_std=0.0052 | patience_run=3
- `ma_pullback|fast=10,pullback_pct=-0.03,slow=60|hold=10` | score=-0.0065 | oos_sharpe=0.2994 | oos_cagr=1.1965 | oos_mdd=-0.9029 | short_long_gap=-0.0049 | split_std=0.0058 | patience_run=3
- `ma_pullback|fast=10,pullback_pct=-0.04,slow=60|hold=10` | score=-0.0449 | oos_sharpe=0.2112 | oos_cagr=0.8812 | oos_mdd=-0.9178 | short_long_gap=-0.0046 | split_std=0.0059 | patience_run=3
- `ma_pullback|fast=10,pullback_pct=-0.05,slow=120|hold=10` | score=-0.0491 | oos_sharpe=0.1430 | oos_cagr=0.7793 | oos_mdd=-0.9153 | short_long_gap=-0.0036 | split_std=0.0053 | patience_run=3

## 재현 방법
- 실행 명령: `python -m research.run --config configs/daily.yaml`
- 결과 테이블: `reports/2026-02-09-2/tables/stage1_candidates.csv`
- 결과 테이블: `reports/2026-02-09-2/tables/final_candidates.csv`
- 결과 테이블: `reports/2026-02-09-2/tables/top_candidates.csv`
