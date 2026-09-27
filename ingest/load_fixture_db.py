"""
Loading the 1,000-person sample CSVs into a small DuckDB file, for use as a
fast, deterministic test fixture (audit determinism tests, dbt CI target).

Same loading pattern as load_raw.py, pointed at data/samples/ instead of
data/raw/. Beneficiary is already a single combined file here (unlike the
raw 3-year split), since build_fixture.py already merged years when it
built the sample.
"""

import duckdb

DB_PATH = "data/claims_ci.duckdb"
SAMPLES_DIR = "data/samples"


def main():
    con = duckdb.connect(DB_PATH)
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")

    tables = ["beneficiary", "inpatient", "outpatient", "pde", "carrier"]
    for table in tables:
        con.execute(f"""
            CREATE OR REPLACE TABLE raw.{table} AS
            SELECT * FROM read_csv_auto('{SAMPLES_DIR}/{table}_sample.csv',
                                         header=true, all_varchar=true)
        """)

    print(f"{'table':<15}{'rows':>12}")
    print("-" * 27)
    for t in tables:
        n = con.execute(f"SELECT COUNT(*) FROM raw.{t}").fetchone()[0]
        print(f"{t:<15}{n:>12,}")

    con.close()


if __name__ == "__main__":
    main()
