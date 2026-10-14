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
Statistic: share of the population with a trailing gap >= N days.

Decision rule (pre-committed, see docs/progress-log.md): a result counts
as a real, actionable dropout signal only if it clears BOTH bars below,
decided before the real statistic was computed:
  - relative: real share >= DECISION_RELATIVE_BAR x the Null A median
  - absolute: real share - Null A median >= DECISION_ABSOLUTE_BAR_PP points
Clearing relative but not absolute means the signal is real but too rare
to be a primary Module D target; Module D instead targets low engagement
(<=2 active months of 6).
"""

import datetime
import json
from pathlib import Path

import duckdb
import numpy as np
import polars as pl

DB_PATH = "data/claims.duckdb"
SEED = 7
CLEAN_WINDOW_END = "2010-01-31"
GAP_DAYS = 180
SENSITIVITY_GAP_DAYS = [90, 120, 180, 270]
N_REDRAWS = 20
DECISION_RELATIVE_BAR = 1.25
DECISION_ABSOLUTE_BAR_PP = 2.0
RESULTS_PATH = Path("reports/audit_results.json")


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
                and fill_date >= date '2008-04-01'
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
        order by eb.beneficiary_id
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
    """Null A (primary): for each person, keep their real fill COUNT
    fixed, draw that many dates from the pooled empirical fill-date
    distribution over the trimmed window, and take the max as their null
    last-fill-date. This mirrors a real person's last fill being whichever
    of their real fills happened latest -- someone with few fills in a
    long window is genuinely more likely to have their last one land
    earlier by chance, and this null reproduces that correctly instead of
    ignoring fill count entirely (an earlier, flawed version of this
    function drew one disconnected date per person regardless of their
    real fill count -- caught and fixed before use, see progress log)."""
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


def build_null_b_trailing_gaps(
    population, analysis_start="2008-04-01", clean_window_end=CLEAN_WINDOW_END, seed=SEED
):
    """Null B (secondary): for each person, keep their real fill COUNT
    fixed, draw that many dates UNIFORMLY (not from the empirical pool)
    across the trimmed window, and take the max as their null
    last-fill-date. Same fill-count-preserving principle as Null A,
    applied from the start this time."""
    rng = np.random.default_rng(seed)
    start = pl.Series([analysis_start]).str.to_date()[0]
    end = pl.Series([clean_window_end]).str.to_date()[0]
    window_days = (end - start).days

    null_last_fill = []
    for n in population["n_fills"].to_list():
        offsets = rng.integers(0, window_days + 1, size=n)
        null_last_fill.append(start + datetime.timedelta(days=int(offsets.max())))

    result = population.select("beneficiary_id", "n_fills").with_columns(
        pl.Series("last_fill_date", null_last_fill)
    )
    return result.with_columns(
        (pl.lit(clean_window_end).str.to_date() - pl.col("last_fill_date"))
        .dt.total_days()
        .alias("trailing_gap_days")
    )


def real_share(population, gap_days):
    """Share of the population with a trailing gap >= gap_days, as a
    percentage."""
    return 100 * (population["trailing_gap_days"] >= gap_days).mean()


def run_gate7_bands(con, n_redraws=N_REDRAWS, seed=SEED, gap_days_list=SENSITIVITY_GAP_DAYS):
    """Run both Gate 7 nulls across n_redraws seeded replicates, collecting
    the share with a trailing gap >= g for every g in gap_days_list from
    EACH replicate -- so the sensitivity sweep reuses the same drawn fake
    worlds at every threshold, rather than redrawing independently per
    threshold. Returns the population and a dict keyed by gap_days, each
    holding the list of per-redraw shares for null_a and null_b."""
    pop = load_gate7_population(con)
    pool = load_pooled_fill_dates(con)

    shares = {g: {"null_a": [], "null_b": []} for g in gap_days_list}

    for i in range(n_redraws):
        null_a = build_null_a_trailing_gaps(pop, pool, seed=seed + i)
        null_b = build_null_b_trailing_gaps(pop, seed=seed + i)
        for g in gap_days_list:
            shares[g]["null_a"].append(real_share(null_a, g))
            shares[g]["null_b"].append(real_share(null_b, g))

    return pop, shares


def gate7_decision(population, shares, gap_days=GAP_DAYS):
    """The pre-committed decision rule, applied at the primary 180-day
    threshold. See module docstring for the rule itself."""
    real = real_share(population, gap_days)
    null_a_band = shares[gap_days]["null_a"]
    null_b_band = shares[gap_days]["null_b"]
    null_a_median = float(np.median(null_a_band))
    null_b_median = float(np.median(null_b_band))

    d_absolute_pp = real - null_a_median
    relative_ratio = real / null_a_median if null_a_median else float("inf")

    clears_relative = relative_ratio >= DECISION_RELATIVE_BAR
    clears_absolute = d_absolute_pp >= DECISION_ABSOLUTE_BAR_PP

    if clears_relative and clears_absolute:
        verdict = "real_dropout_process"
        module_d_target = "terminal_stop_180d"
    elif clears_relative and not clears_absolute:
        verdict = "detectable_but_too_rare"
        module_d_target = "low_engagement_le2_active_months_of_6"
    else:
        verdict = "arithmetic"
        module_d_target = None

    return {
        "gap_days": gap_days,
        "real_share_pct": real,
        "null_a_median_pct": null_a_median,
        "null_a_band_pct": [min(null_a_band), max(null_a_band)],
        "null_b_median_pct": null_b_median,
        "null_b_band_pct": [min(null_b_band), max(null_b_band)],
        "relative_bar": DECISION_RELATIVE_BAR,
        "relative_ratio": relative_ratio,
        "clears_relative_bar": clears_relative,
        "absolute_bar_pp": DECISION_ABSOLUTE_BAR_PP,
        "d_absolute_pp": d_absolute_pp,
        "clears_absolute_bar": clears_absolute,
        "verdict": verdict,
        "module_d_target": module_d_target,
    }


def gate7_sensitivity_sweep(population, shares, gap_days_list=SENSITIVITY_GAP_DAYS):
    """Real share vs. both null medians/bands at each cutoff in
    gap_days_list, reusing the same drawn replicates from run_gate7_bands."""
    sweep = {}
    for g in gap_days_list:
        null_a_band = shares[g]["null_a"]
        null_b_band = shares[g]["null_b"]
        sweep[g] = {
            "real_share_pct": real_share(population, g),
            "null_a_median_pct": float(np.median(null_a_band)),
            "null_a_band_pct": [min(null_a_band), max(null_a_band)],
            "null_b_median_pct": float(np.median(null_b_band)),
            "null_b_band_pct": [min(null_b_band), max(null_b_band)],
        }
    return sweep


if __name__ == "__main__":
    con = duckdb.connect(DB_PATH, read_only=True)

    print(f"Running {N_REDRAWS} redraws across thresholds {SENSITIVITY_GAP_DAYS} days...")
    pop, shares = run_gate7_bands(con, n_redraws=N_REDRAWS, gap_days_list=SENSITIVITY_GAP_DAYS)
    print(f"Gate 7 population: {pop.height:,}")

    decision = gate7_decision(pop, shares, gap_days=GAP_DAYS)
    sweep = gate7_sensitivity_sweep(pop, shares, gap_days_list=SENSITIVITY_GAP_DAYS)

    print(f"\n=== GATE 7 DECISION ({GAP_DAYS}-day primary) ===")
    for k, v in decision.items():
        print(f"  {k}: {v}")

    print("\n=== SENSITIVITY SWEEP ===")
    for g, vals in sweep.items():
        print(
            f"  {g}d: real={vals['real_share_pct']:.2f}%  "
            f"null_a_median={vals['null_a_median_pct']:.2f}%  "
            f"null_b_median={vals['null_b_median_pct']:.2f}%"
        )

    existing = json.loads(RESULTS_PATH.read_text()) if RESULTS_PATH.exists() else {}
    existing["gate7_terminal_stop"] = {
        "population": pop.height,
        "decision": decision,
        "sensitivity_sweep": sweep,
        "n_redraws": N_REDRAWS,
        "seed": SEED,
    }
    RESULTS_PATH.parent.mkdir(exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(existing, indent=2, default=str))
    print(f"\nResults written to {RESULTS_PATH}")

    con.close()
