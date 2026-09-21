"""
Build a 1,000-beneficiary CI fixture from the full raw dataset.

Samples DESYNPUF_IDs from raw.beneficiary, then pulls every row belonging
to those beneficiaries from all the 8 raw tables, writing each to
data/samples/ as CSV. This fixture is what CI (Week 8) runs dbt build
against, so it must be small (<50MB total) and self-consistent: every
claim's DESYNPUF_ID must exist in the sampled beneficiary set.
"""

import duckdb

DB_PATH = "data/claims.duckdb"
SAMPLES_DIR = "data/samples"
N_BENEFICIARIES = 1000
SEED = 7  # Coz 007 was not possible due leading zeros.

TABLES = ["beneficiary", "inpatient", "outpatient", "pde", "carrier"]


def main():
    con = duckdb.connect(DB_PATH)

    # Sample the N beneficiary IDs reproducibly
    con.execute(f"SELECT setseed({SEED/2147483647})")
    sample_ids = con.execute(f"""
        SELECT DESYNPUF_ID
        FROM (SELECT DISTINCT DESYNPUF_ID FROM raw.beneficiary)
        USING SAMPLE {N_BENEFICIARIES} (reservoir)
    """).fetchall()

    ids = [row[0] for row in sample_ids]
    print(f"Sampled {len(ids)} distinct beneficiary IDs")

    # Register the sampled IDs as a temp table, so every extraction
    # query can just join/filter against it
    con.execute("CREATE OR REPLACE TEMP TABLE sample_ids (DESYNPUF_ID VARCHAR)")
    con.executemany("INSERT INTO sample_ids VALUES(?)", [(i,) for i in ids])

    # For each raw table, extract only rows belonging to sampled IDs,
    # and write to CSV
    for table in TABLES:
        out_path = f"{SAMPLES_DIR}/{table}_sample.csv"
        con.execute(f"""
            COPY(
                SELECT r.*
                FROM raw.{table} r
                JOIN sample_ids s ON r.DESYNPUF_ID = s.DESYNPUF_ID
            ) TO '{out_path}' (HEADER, DELIMITER ',')
        """)
        n_rows = con.execute(f"""
            SELECT COUNT(*) FROM raw.{table} r
            JOIN sample_ids s ON r.DESYNPUF_ID = s.DESYNPUF_ID
        """).fetchone()[0]
        print(f"{table:<15}{n_rows:>10,} rows -> {out_path}")
    con.close()


if __name__ == "__main__":
    main()
