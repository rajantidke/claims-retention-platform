"""
Module B baseline parameters, anchored to the real distribution.

The experiment being sized: a hypothetical
pharmacy-engagement outreach program. Randomize full-year Part D
enrollees on 2009-02-01. Pre-period: Aug 2008 - Jan 2009 (6 months).
Post-period: Feb 2009 - Jul 2009 (6 months). Primary metric: active
months in the post-period (0-6, from fct_monthly_active.is_active).

Why 2009-02-01: pre + post is 12 months, and the clean analysis window is
Apr 2008 - Jan 2010 (22 months). Randomizing here places both periods
entirely inside the window with 4 months of margin at the front (Apr-Jul
2008 unused) and 6 at the back (Aug 2009-Jan 2010 unused) - clear of the
2008 ramp and the 2010 decline (Gate 4).

Population: restricted to beneficiaries who are alive at the end of the
post-period (2009-07-01) and have a full year of Part D coverage in BOTH
2008 and 2009 - the same restriction Gate 7 uses and for the same reason:
month-level activity is only trustworthy for beneficiaries with a full
year of coverage that year (int_member_months.has_full_year_part_d).

Two metrics, both sized in Part 2:
  - primary: mean/SD of post-period active months (continuous, 0-6)
  - secondary: baseline rate of <=2 active months of 6 (binary) - this
    is exactly Module D's target (Gate 7), which keeps the two modules
    telling one story.

Also computes rho (pre-period active months vs. post-period active
months), which Part 4 (CUPED) uses directly as its covariate correlation.
"""

import json
from pathlib import Path

import duckdb
import polars as pl

DB_PATH = "data/claims.duckdb"
PRE_START = "2008-08-01"
PRE_END = (
    "2009-02-01"  # exclusive upper bound on month_start; equals POST_START, periods are adjacent
)
POST_START = "2009-02-01"
POST_END = "2009-08-01"  # exclusive upper bound on month_start
RANDOMIZATION_DATE = "2009-02-01"
RESULTS_PATH = Path("reports/harness_validation.json")


def load_population(con):
    """Per-beneficiary pre- and post-period active-month counts (0-6
    each), restricted to beneficiaries alive at the end of the
    post-period with a full year of Part D coverage in both 2008 and
    2009 (same restriction and rationale as Gate 7's population)."""
    return con.execute(f"""
        with eligible_beneficiaries as (
            select beneficiary_id
            from main_marts.fct_monthly_active
            where month_start = date '{POST_START}'
                and is_alive
            intersect
            select beneficiary_id
            from main_marts.fct_monthly_active
            where source_year = 2008 and has_full_year_part_d
            intersect
            select beneficiary_id
            from main_marts.fct_monthly_active
            where source_year = 2009 and has_full_year_part_d
        ),

        pre_period as (
            select
                beneficiary_id,
                sum(case when is_active then 1 else 0 end) as pre_active_months
            from main_marts.fct_monthly_active
            where month_start >= date '{PRE_START}'
                and month_start < date '{PRE_END}'
            group by 1
        ),

        post_period as (
            select
                beneficiary_id,
                sum(case when is_active then 1 else 0 end) as post_active_months
            from main_marts.fct_monthly_active
            where month_start >= date '{POST_START}'
                and month_start < date '{POST_END}'
            group by 1
        )

        select
            eb.beneficiary_id,
            coalesce(pre.pre_active_months, 0) as pre_active_months,
            coalesce(post.post_active_months, 0) as post_active_months

        from eligible_beneficiaries eb
        left join pre_period pre on eb.beneficiary_id = pre.beneficiary_id
        left join post_period post on eb.beneficiary_id = post.beneficiary_id
        order by eb.beneficiary_id
    """).pl()


def compute_baseline_parameters(population):
    """The four numbers Part 1 hands to Part 2 (power/MDE) and Part 4
    (CUPED): mean/SD of post-period active months, baseline rate of <=2
    active months (Module D's target), Pearson rho between pre- and
    post-period active months, and the eligible population size."""
    post = population["post_active_months"]

    n = population.height
    mean_post = post.mean()
    sd_post = post.std()
    baseline_le2_rate = (post <= 2).sum() / n
    rho = population.select(pl.corr("pre_active_months", "post_active_months")).item()

    return {
        "eligible_population": n,
        "mean_post_active_months": mean_post,
        "sd_post_active_months": sd_post,
        "baseline_le2_active_months_rate": baseline_le2_rate,
        "pre_post_pearson_rho": rho,
        "pre_period": [PRE_START, PRE_END],
        "post_period": [POST_START, POST_END],
        "randomization_date": RANDOMIZATION_DATE,
    }


def run_and_save(con):
    population = load_population(con)
    params = compute_baseline_parameters(population)

    output_path = RESULTS_PATH
    if output_path.exists():
        existing = json.loads(output_path.read_text())
    else:
        existing = {}

    existing["baseline_parameters"] = params
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(json.dumps(existing, indent=2, default=str))

    return params


if __name__ == "__main__":
    con = duckdb.connect(DB_PATH, read_only=True)
    params = run_and_save(con)
    print(f"Eligible population: {params['eligible_population']:,}")
    print(
        f"Post-period active months: mean {params['mean_post_active_months']:.3f}, "
        f"SD {params['sd_post_active_months']:.3f}"
    )
    print(f"Baseline <=2 active months rate: {params['baseline_le2_active_months_rate']:.4f}")
    print(f"Pre/post Pearson rho: {params['pre_post_pearson_rho']:.4f}")
    con.close()
