.PHONY: setup download ingest test clean

setup:
	uv venv && uv pip install -e ".[dev]" && pre-commit install

download:
	@echo "Download is manual for this project — see docs/progress-log.md (Step 3)."
	@echo "Expected files already present under data/raw/."

ingest:
	python -m ingest.load_raw

test:
	pytest -q

clean:
	rm -f data/claims.duckdb data/claims.duckdb.wal
