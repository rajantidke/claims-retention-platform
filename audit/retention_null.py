"""
Retention null overlay: does the real retention curve from
fct_cohort_retention differ from what fill count and observation span
alone would produce?

PRE-COMMITTED DESIGN (written before any redraw band was drawn)

Primary endpoint: pooled month-6 retention (share of entrants active in the
calendar month six months after their entry month). Every entrant is eligible:
the latest entry month (Jul 2009) + 6 months = Jan 2010, inside
clean_window_end. The full retention curve is descriptive only.

Null A' (governs the ruling): span-anchored redraw. Each beneficiary's first
and last fill in the analysis window are held fixed; interior fills are
redrawn uniformly within that span. Fill count and span survive; only
within-span timing is destroyed. Same machinery as Gate 6 Test 2. Entry is
recomputed from the redrawn dates in every replicate, and null cohort sizes
are reported beside the real one. 20 redraws give a band; the null median is
the reference value.

Null B (context only, does not govern the ruling): pooled draw of fill dates
from the whole file, keeping each beneficiary's fill count. It also destroys
span, so the gap between A' and B is the share of retention shape
attributable to span structure.

Effective power of A': entrants with fewer than 3 fills are unchanged by the
redraw. Report their share. Secondary comparison, pre-specified: entrants
with 4 or more fills only.

Threshold: T = max(3 pp, 0.15 x null_A'_median_month6).
D = null_A'_median - real (positive means real sits below null).

  Real inside the A' band          -> arithmetic: retention is intensity-driven
  Outside band, |D| < T            -> arithmetic, residual reported as a number
  Outside band, D >= T             -> real dropout process beyond intensity
  Outside band, -D >= T            -> investigate before publishing. With span
                                      held fixed, a bug leads; genuine
                                      within-span regularity is unlikely
                                      (Gate 6 CV of gaps 0.937 vs 0.938)

Disclosure: the real month-6 value (23.1%) was known when the null's design
was finalised. The design change was driven by the span-confounding argument
from Gate 6 Test 2, which does not refer to that value, and the threshold
was fixed as a formula before any null value existed.

"""

import duckdb
import numpy as np
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


def build_empirical_null(fills, seed=SEED):
    """Redraw each beneficiary's fill dates from the pooled real fill-date
    distribution, keeping their own fill count fixed. Conservative: if
    real churn is common, the pooled distribution is itself depleted near
    the window's end, so this null partially absorbs the signal it tests.

    Vectorized: one single draw of len(fills) dates from the pool,
    assigned back onto the original beneficiary_id column in order. This
    keeps each beneficiary's fill count exactly fixed (same number of
    rows per beneficiary as the real data) while randomizing which dates
    they get, without looping per beneficiary.
    """
    rng = np.random.default_rng(seed)
    pool = fills["fill_date"]

    idx = rng.integers(0, len(pool), size=len(pool))

    return fills.select("beneficiary_id").with_columns(pool.gather(idx).alias("fill_date"))


def build_span_anchored_null(fills, seed=SEED):
    """Redraw each beneficiary's INTERIOR fill dates uniformly within their
    own observation span, holding their first and last fill fixed. Fill
    count and span survive; only within-span timing is destroyed. Same
    logic as Gate 6 Test 2, vectorized here rather than looped per person.

    Entrants with fewer than 3 fills have no interior dates to redraw and
    pass through unchanged (identity rows) -- this is the effective-power
    caveat from the pre-commit docstring, reported separately.
    """
    rng = np.random.default_rng(seed)
    span = fills.group_by("beneficiary_id").agg(
        pl.col("fill_date").min().alias("first_date"),
        pl.col("fill_date").max().alias("last_date"),
        pl.len().alias("n_fills"),
    )
    tagged = (
        fills.join(span, on="beneficiary_id", how="left")
        .with_columns(pl.col("fill_date").rank("ordinal").over("beneficiary_id").alias("row_rank"))
        .with_columns(
            (pl.col("row_rank") == 1).alias("is_first"),
            (pl.col("row_rank") == pl.col("n_fills")).alias("is_last"),
        )
    )
    span_days = (tagged["last_date"] - tagged["first_date"]).dt.total_days()
    u = rng.random(tagged.height)
    offset_days = (u * (span_days + 1)).floor().cast(pl.Int32)
    redrawn_interior_date = tagged["first_date"] + pl.duration(days=offset_days)

    result = tagged.with_columns(
        pl.when(pl.col("is_first") | pl.col("is_last"))
        .then(pl.col("fill_date"))
        .otherwise(redrawn_interior_date)
        .alias("fill_date_new")
    ).select("beneficiary_id", pl.col("fill_date_new").alias("fill_date"))
    return result


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
