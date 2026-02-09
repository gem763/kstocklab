# 데이터 스키마

이 저장소는 필드별 parquet 파일을 `data/` 아래에 저장합니다.

현재 파일 예시:

- `open.parquet`
- `high.parquet`
- `low.parquet`
- `close.parquet`
- `volume.parquet`
- `amount.parquet`
- `marketcap.parquet`
- `shares.parquet`
- `market_index_close.parquet` (선택, KOSPI/KOSDAQ/KOSPI200 종가)

기본 가정:

- wide 형식: index=`date`, columns=`ticker`
- 값은 각 필드의 수치형 데이터
