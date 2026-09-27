.PHONY: setup download ingest audit build dbt-deps dbt-test dbt-docs test clean

setup:
	uv venv && uv pip install -e ".[dev]" && pre-commit install

download:
	@echo "Download is manual for this project — see docs/progress-log.md (Step 3)."
	@echo "Expected files already present under data/raw/."

ingest:
	python -m ingest.load_raw

audit:
	python -m audit.fidelity

DBT = dbt

dbt-deps:
	cd transform && dbt deps

build:
	$(DBT) build --project-dir transform --profiles-dir transform

dbt-test:
	$(DBT) test --project-dir transform --profiles-dir transform

dbt-docs:
	$(DBT) docs generate --project-dir transform --profiles-dir transform && $(DBT) docs serve --project-dir transform --profiles-dir transform

test:
	pytest -q

clean:
	rm -f data/claims.duckdb data/claims.duckdb.wal
