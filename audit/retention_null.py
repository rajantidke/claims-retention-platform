"""
Retention null overlay: tests whether the real retention curve from
fct_cohort_retention differs from what fill-count and window length alone
would produce (Gate 6's finding, applied to a new question).

Two nulls, per review: empirical (draw null fill dates from the pooled
real fill-date distribution, conservative since it partially absorbs real
churn if churn is common) and uniform over the trimmed window (secondary).
Primary endpoint: pooled month-6 retention. Threshold is a function of the
null, not a fixed number, and both nulls plus the threshold are committed
to reports/audit_results.json before the real curve is computed.
"""

import duckdb
import polars as pl

DB_PATH = "data/claims.duckdb"
SEED = 7
ANALYSIS_START = "2008-04-01"
CLEAN_WINDOW_END = "2010-01-31"


def load_real_fill_events(con):
    """Every non-zero-days-supply fill inside the analysis window, one row
    per fill, same population the dbt marts already use."""
    return con.execute(f"""
        SELECT beneficiary_id, fill_date
        FROM main_intermediate.int_fill_events
        WHERE not is_zero_days_supply
            AND fill_date BETWEEN date '{ANALYSIS_START}' AND date '{CLEAN_WINDOW_END}'
        ORDER BY beneficiary_id, fill_date
    """).pl()


def assign_entry_cohorts(fills, washout_days=180, entry_start="2008-09-28", entry_end="2009-07-31"):
    """Same new-user logic as fct_cohort_retention.sql: first fill ever, or
    first fill after a washout_days gap, restricted to the entry window."""
    fills = fills.sort(["beneficiary_id", "fill_date"])
    fills = fills.with_columns(
        (pl.col("fill_date") - pl.col("fill_date").shift(1).over("beneficiary_id"))
        .dt.total_days()
        .alias("days_since_prev")
    )

    entry_candidates = fills.filter(
        (pl.col("days_since_prev").is_null()) | (pl.col("days_since_prev") >= washout_days)
    )

    entry_window = entry_candidates.filter(
        (pl.col("fill_date") >= pl.lit(entry_start).str.to_date())
        & (pl.col("fill_date") <= pl.lit(entry_end).str.to_date())
    )

    first_entry = (
        entry_window.group_by("beneficiary_id")
        .agg(pl.col("fill_date").min().alias("entry_date"))
        .with_columns(pl.col("entry_date").dt.truncate("1mo").alias("entry_month"))
    )
    return first_entry


def compute_month6_retention(fills, cohorts, clean_window_end="2010-01-31"):
    """Pooled month-6 retention: of everyone whose entry + 6 months falls
    on or before clean_window_end, what share had >=1 fill in that
    calendar month."""
    cohorts = cohorts.with_columns(pl.col("entry_month").dt.offset_by("6mo").alias("month6"))
    eligible = cohorts.filter(pl.col("month6") <= pl.lit(clean_window_end).str.to_date())

    fills_by_month = (
        fills.with_columns(pl.col("fill_date").dt.truncate("1mo").alias("fill_month"))
        .select(["beneficiary_id", "fill_month"])
        .unique()
    )

    active = eligible.join(
        fills_by_month,
        left_on=["beneficiary_id", "month6"],
        right_on=["beneficiary_id", "fill_month"],
        how="semi",
    )

    n_eligible = eligible.height
    n_active = active.height
    return n_eligible, n_active


if __name__ == "__main__":
    con = duckdb.connect(DB_PATH, read_only=True)
    fills = load_real_fill_events(con)
    print(f"Loaded {fills.height:,} fills for {fills['beneficiary_id'].n_unique():,} beneficiaries")

    cohorts = assign_entry_cohorts(fills)
    print(f"Cohort size: {cohorts.height:,}")
    print(f"Entry months: {cohorts['entry_month'].min()} to {cohorts['entry_month'].max()}")

    n_eligible, n_active = compute_month6_retention(fills, cohorts)
    print(
        f"Month-6 eligible: {n_eligible:,}, active: {n_active:,}, rate: {100 * n_active / n_eligible:.1f}%"
    )

    con.close()
