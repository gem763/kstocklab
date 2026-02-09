# kstocklab

한국 주식 일별 parquet 데이터를 기반으로 패턴 연구를 수행하는 저장소입니다.

## 목표

- 단일 실행 진입점: `python -m research.run --config configs/daily.yaml`
- 필수 산출물: `reports/YYYY-MM-DD*/summary.md`
- 메모리 파일 지속 업데이트: `research/memory/*`
- 후보 생성 -> 워크포워드 검증 -> 순위화 -> 리포트 자동화
- OOS 구간별 단기/장기 통계 비교와 인내구간(연속 부진 구간) 진단 반영
- 레거시 문헌 시작점: `static/패턴은 정말 존재하는가.pdf`

## 빠른 시작

```bash
make setup
make smoke
```

또는

```bash
python -m research.run --config configs/smoke.yaml
```

## 일일 실행

```bash
make daily
```

생성 산출물:

- `reports/YYYY-MM-DD*/summary.md`
- `reports/YYYY-MM-DD*/tables/stage1_candidates.csv`
- `reports/YYYY-MM-DD*/tables/final_candidates.csv`
- `reports/YYYY-MM-DD*/tables/top_candidates.csv`
- `research/memory/ledger.parquet` 누적 갱신

## 시장지수 데이터

옵션 데이터 제공자 설치:

```bash
make setup-market
```

시장지수 parquet 수집:

```bash
make fetch-market
```

위 명령은 `data/market_index_close.parquet`를 생성하며, 설정 파일의 시장 레짐 필터에서 사용할 수 있습니다.
