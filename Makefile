PY ?= python

.PHONY: setup setup-market smoke daily start pattern-research data-check fetch-market

setup:
	$(PY) -m pip install -r requirements.txt

setup-market:
	$(PY) -m pip install -r requirements-market.txt

smoke:
	$(PY) -m research.run --config configs/smoke.yaml

daily:
	$(PY) -m research.run --config configs/daily.yaml

start: daily

pattern-research: daily

data-check:
	$(PY) research/data_check.py

fetch-market:
	$(PY) scripts/fetch_market_index.py --provider pykrx --start 2000-01-01 --out data/market_index_close.parquet
