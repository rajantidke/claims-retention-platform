"""
Gate 7: terminal stopping. The last open design question in the project.

Gate 6 Test 2 anchored each person's first and last fill, so it tested
timing WITHIN an observation span, never whether the END of that span --
the last fill happening well before clean_window_end -- looks like a real
behavioral stop rather than chance (people simply ran out of window to be
observed in).

Population: alive through clean_window_end, full-year Part D in BOTH 2008
and 2009 (the only two full years inside the clean window), at least one
fill in [derived_start, clean_window_end].

Real trailing gap = clean_window_end - last_fill_date.
Statistic: share of the population with a trailing gap >= 180 days.
"""

import duckdb
import numpy as np
import polars as pl

DB_PATH = "data/claims.duckdb"
SEED = 7
CLEAN_WINDOW_END = "2010-01-31"
GAP_DAYS = 180


def load_gate7_population(con):
    """Alive through clean_window_end, full-year Part D in both 2008 and
    2009, with >=1 fill inside the clean window."""
    return con.execute(f"""
        with eligible_beneficiaries as (
            select beneficiary_id
            from main_intermediate.int_member_months
            where month_start = date_trunc('month', date '{CLEAN_WINDOW_END}')::date
                and is_alive
            intersect
            select beneficiary_id
            from main_intermediate.int_member_months
            where source_year = 2008 and has_full_year_part_d
            intersect
            select beneficiary_id
            from main_intermediate.int_member_months
            where source_year = 2009 and has_full_year_part_d
        ),
        last_fills as (
            select
                beneficiary_id,
                max(fill_date) as last_fill_date,
                count(*) as n_fills

            from main_intermediate.int_fill_events
            where not is_zero_days_supply
                and in_clean_window
            group by 1
        )

        select
            eb.beneficiary_id,
            lf.last_fill_date,
            lf.n_fills,
            date '{CLEAN_WINDOW_END}' - lf.last_fill_date as trailing_gap_days

        from eligible_beneficiaries eb
        inner join last_fills lf on eb.beneficiary_id = lf.beneficiary_id
    """).pl()


def load_pooled_fill_dates(con, analysis_start="2008-04-01", clean_window_end=CLEAN_WINDOW_END):
    """All real fill dates inside the trimmed window [analysis_start,
    clean_window_end], the pool Null A draws from."""
    return con.execute(f"""
        SELECT fill_date
        FROM main_intermediate.int_fill_events
        WHERE not is_zero_days_supply
            AND fill_date BETWEEN date '{analysis_start}' AND date '{clean_window_end}'
        ORDER BY fill_date
    """).pl()["fill_date"]


def build_null_a_trailing_gaps(population, pool, seed=SEED):
    """Null A: for each person, keep their real fill COUNT fixed, draw
    that many dates from the pooled empirical fill-date distribution over
    the trimmed window, and take the max as their null last-fill-date.
    This mirrors a real person's last fill being whichever of their real
    fills happened latest -- someone with few fills in a long window is
    genuinely more likely to have their last one land earlier by chance,
    and this null reproduces that correctly instead of ignoring fill
    count entirely (an earlier, flawed version of this function drew one
    disconnected date per person regardless of their real fill count --
    caught and fixed before use, see progress log)."""
    rng = np.random.default_rng(seed)
    pool_size = pool.len()

    null_last_fill = []
    for n in population["n_fills"].to_list():
        idx = rng.integers(0, pool_size, size=n)
        drawn = pool.gather(idx)
        null_last_fill.append(drawn.max())

    result = population.select("beneficiary_id", "n_fills").with_columns(
        pl.Series("last_fill_date", null_last_fill)
    )
    return result.with_columns(
        (pl.lit(CLEAN_WINDOW_END).str.to_date() - pl.col("last_fill_date"))
        .dt.total_days()
        .alias("trailing_gap_days")
    )


if __name__ == "__main__":
    con = duckdb.connect(DB_PATH, read_only=True)
    pop = load_gate7_population(con)
    print(f"Gate 7 population: {pop.height:,}")

    share_180plus = (pop["trailing_gap_days"] >= GAP_DAYS).mean()
    print(f"Share with trailing gap >= {GAP_DAYS} days: {100 * share_180plus:.1f}%")

    con.close()
