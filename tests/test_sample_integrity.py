"""
Sample 1 vs Sample 20 verification.

CMS's SynPUF download page mislabels the 2010 Beneficiary Summary File link.
It actually points to Sample 20's file. If that swap happened silently,
DESYNPUF_IDs in the 2010 file would barely overlap with 2008/2009, and every
longitudinal analysis downstream would be silently wrong.

See docs/progress-log.md (Week 2, Step 3) for the manual verification this
test formalizes, and the DE-SynPUF codebook Table 2 for the expected
per-sample beneficiary counts this checks against.
"""

import duckdb
import pytest

RAW_DIR = "data/raw"

# Expected distinct-beneficiary counts for Sample 1, from codebook Table 2.
EXPECTED_COUNTS = {
    2008: 116_352,
    2009: 114_538,
    2010: 112_754,
}

FILES = {
    2008: f"{RAW_DIR}/DE1_0_2008_Beneficiary_Summary_File_Sample_1.csv",
    2009: f"{RAW_DIR}/DE1_0_2009_Beneficiary_Summary_File_Sample_1.csv",
    2010: f"{RAW_DIR}/DE1_0_2010_Beneficiary_Summary_File_Sample_1.csv",
}


@pytest.fixture(scope="module")
def con():
    return duckdb.connect()


def distinct_id_count(con, path):
    return con.execute(
        f"SELECT COUNT(DISTINCT DESYNPUF_ID) FROM read_csv_auto('{path}', header=true)"
    ).fetchone()[0]


@pytest.mark.parametrize("year", [2008, 2009, 2010])
def test_beneficiary_count_matches_sample_1(con, year):
    """
    Each year's distinct beneficiary count should match Sample 1's published figures.

    """
    actual = distinct_id_count(con, FILES[year])
    expected = EXPECTED_COUNTS[year]
    assert actual == expected, (
        f"{year}: expected {expected} distinct beneficiaries (Sample 1 per codebook), "
        f"got {actual}. If this is close to 116,375 for 2010, you likely downloaded "
        f"the mislabeled Sample 20 file instead of Sample 1."
    )


def test_2010_overlaps_heavily_with_2008(con):
    """
    2010 beneficiaries should almost entirely be a subset of 2008's (attrition
    via death, no new entrants into this closed cohort). Near-zero overlap
    means the 2010 file is not actually Sample 1.

    """
    overlap = con.execute(f"""
        SELECT count(*) FROM (
            SELECT DESYNPUF_ID FROM read_csv_auto('{FILES[2008]}', header=true)
            INTERSECT
            SELECT DESYNPUF_ID FROM read_csv_auto('{FILES[2010]}', header=true)
        )
    """).fetchone()[0]

    count_2010 = distinct_id_count(con, FILES[2010])
    pct_of_2010_found_in_2008 = 100 * overlap / count_2010

    assert pct_of_2010_found_in_2008 > 95, (
        f"Only {pct_of_2010_found_in_2008:.1f}% of 2010 beneficiaries found in 2008 "
        f"(expected >95%). This strongly suggests the 2010 file is Sample 20, not Sample 1."
    )
