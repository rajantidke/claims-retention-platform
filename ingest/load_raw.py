"""
Loading the raaw Synpuf csvs into Duckdb without any transformation.

Everything loads as a VARCHAR by menas of (all_varchar=true)
to protect the leading-zero codes(NDC, ICD-9, state/county codes)
from DuckDB's type inference silently coercing them to integers
and destroying the leading zeros.

Type casting belongs in dbt staging (approx. Week 3 work), not here. Keeping raw
untouched means we can always go back to source.
"""

import duckdb

DB_PATH = "data/claims.duckdb"
RAW_DIR = "data/raw"


def main():
    # Created a new empty database file
    con = duckdb.connect(DB_PATH)
    # con is the handle for running SQL with that file
    # con opens the connectioon and then we create the schema
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")

    # Loading the beneficiary files
    # --- Beneficiary: union three years,
    # tagging each with source_year
    con.execute(f"""
        CREATE OR REPLACE TABLE raw.beneficiary AS
        SELECT *, 2008 as source_year
        FROM read_csv_auto('{RAW_DIR}/DE1_0_2008_Beneficiary_Summary_File_Sample_1.csv',
                            header=true, all_varchar=true)
        UNION ALL BY NAME
        SELECT *, 2009 as source_year
        FROM read_csv_auto('{RAW_DIR}/DE1_0_2009_Beneficiary_Summary_File_Sample_1.csv',
                            header=true, all_varchar=true)

        UNION ALL BY NAME
        SELECT *, 2010 as source_year
        FROM read_csv_auto('{RAW_DIR}/DE1_0_2010_Beneficiary_Summary_File_Sample_1.csv',
                            header=true, all_varchar=true)
    """)

    # Loading the inpatient,outpaitent, PDE files
    # --- Inpatient (already spans 2008-2010 in one file) ---
    con.execute(f"""
        CREATE OR REPLACE TABLE raw.inpatient AS
        SELECT * FROM read_csv_auto('{RAW_DIR}/DE1_0_2008_to_2010_Inpatient_Claims_Sample_1.csv',
                                    header=true, all_varchar=true)
    """)

    # --- Outpatient ---
    con.execute(f"""
        CREATE OR REPLACE TABLE raw.outpatient AS
        SELECT * FROM read_csv_auto('{RAW_DIR}/DE1_0_2008_to_2010_Outpatient_Claims_Sample_1.csv',
                                     header=true, all_varchar=true)
    """)

    # --- PDE ---
    con.execute(f"""
        CREATE OR REPLACE TABLE raw.pde AS
        SELECT * FROM read_csv_auto('{RAW_DIR}/DE1_0_2008_to_2010_Prescription_Drug_Events_Sample_1.csv',
                                     header=true, all_varchar=true)
    """)

    # Loading the carrier claims files: union of samples A and B
    con.execute(f"""
        CREATE OR REPLACE TABLE raw.carrier AS
        SELECT * FROM read_csv_auto('{RAW_DIR}/DE1_0_2008_to_2010_Carrier_Claims_Sample_1A.csv',
                                    header=true, all_varchar=true)

        UNION ALL BY NAME
        SELECT * FROM read_csv_auto('{RAW_DIR}/DE1_0_2008_to_2010_Carrier_Claims_Sample_1B.csv',
                                            header=true, all_varchar=true)



    """)

    # Summary table
    tables = ["beneficiary", "inpatient", "outpatient", "pde", "carrier"]
    print(f"{'table':<15}{'rows':>12}")
    print("-" * 27)
    for t in tables:
        n = con.execute(f"SELECT COUNT(*) FROM raw.{t}").fetchone()[0]
        print(f"{t:<15}{n:>12,}")

    con.close()


if __name__ == "__main__":
    main()
