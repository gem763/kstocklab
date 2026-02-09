# 일일 연구 프롬프트

오늘의 자율 패턴 연구를 시작한다.

필수 절차:

1. `AGENTS.md`의 저장소 규칙을 먼저 읽는다.
2. `static/패턴은 정말 존재하는가.pdf`는 레거시 가설 소스로 취급한다.
3. 레거시 주장을 그대로 신뢰하지 말고, 워크포워드 OOS 지표로 검증한다.
4. 웹 접근이 가능하고 최신 근거가 필요하면 최근 참고문헌을 찾아 `configs/recent_sources.yaml`에 기록한다.
5. 최초 1회 또는 새 클라우드 세션이면 의존성을 설치한다:
   - `make setup`
6. 아래 명령을 실행한다:
   - `python -m research.run --config configs/daily.yaml`
   - `research.max_minutes` 시간 예산에 도달하면 종료한다.
7. 산출물을 확인한다:
   - `reports/YYYY-MM-DD*/summary.md`
   - `reports/YYYY-MM-DD*/tables/*.csv`
   - `research/memory/ledger.parquet` 반영
   - `research/memory/backlog.md`, `research/memory/lessons.md` 업데이트
