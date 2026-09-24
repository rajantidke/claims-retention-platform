"""
This script is a Fidelity audit. It validates which properties of the DE-SynPUF dataset survive
its synthesis/de-identification process, and which don't.

I have designed six gates, each testing a specific assumption before it gets relied on in
later modules. See docs/fidelity_audit.md for full narrative context:
this module produces the numbers that document cites.
"""

import duckdb
import numpy as np
import polars as pl
from scipy import stats

DB_PATH = "data/claims.duckdb"
SEED = 7  # Like always, 007 is unavailable.


def gate1_refill_pairs(con):
    """Population-wide check: does a beneficiary ever refill the exact
    same product code, or the same labeler, more than once?"""
    product_pairs = con.execute("""
        SELECT COUNT(*) AS pairs, SUM(CASE WHEN n >= 2 THEN 1 ELSE 0 END) AS pairs_with_refill
        FROM (
            SELECT DESYNPUF_ID, PROD_SRVC_ID, COUNT(*) AS n
            FROM raw.pde
            GROUP BY DESYNPUF_ID, PROD_SRVC_ID
        )
    """).fetchone()

    labeler_pairs = con.execute("""
        SELECT COUNT(*) AS pairs, SUM(CASE WHEN n >= 2 THEN 1 ELSE 0 END) AS pairs_with_refill
        FROM (
            SELECT DESYNPUF_ID, SUBSTRING(PROD_SRVC_ID, 1, 5) AS labeler, COUNT(*) AS n
            FROM raw.pde
            GROUP BY DESYNPUF_ID, labeler
        )
    """).fetchone()

    return {
        "product_total_pairs": product_pairs[0],
        "product_pairs_with_refill": product_pairs[1],
        "product_pct_refill": 100 * product_pairs[1] / product_pairs[0],
        "labeler_total_pairs": labeler_pairs[0],
        "labeler_pairs_with_refill": labeler_pairs[1],
        "labeler_pct_refill": 100 * labeler_pairs[1] / labeler_pairs[0],
    }


def gate2_labeler_concentration_null(con):
    """Is a beneficiary's tendency to cluster fills around one labeler a
    real personal trait, or indistinguishable from random chance?"""
    pde_labelers = con.execute("""
        SELECT DESYNPUF_ID, SUBSTRING(PROD_SRVC_ID, 1, 5) AS labeler
        FROM raw.pde
        ORDER BY DESYNPUF_ID, PDE_ID
    """).pl()

    real_concentration = (
        pde_labelers.group_by(["DESYNPUF_ID", "labeler"])
        .len()
        .group_by("DESYNPUF_ID")
        .agg(
            [
                pl.col("len").max().alias("top_labeler_fills"),
                pl.col("len").sum().alias("total_fills"),
            ]
        )
        .with_columns(
            (pl.col("top_labeler_fills") / pl.col("total_fills")).alias("top_labeler_share")
        )
    )

    shuffled_labelers = pde_labelers.with_columns(
        pl.col("labeler").shuffle(seed=SEED).alias("labeler")
    )
    shuffled_concentration = (
        shuffled_labelers.group_by(["DESYNPUF_ID", "labeler"])
        .len()
        .group_by("DESYNPUF_ID")
        .agg(
            [
                pl.col("len").max().alias("top_labeler_fills"),
                pl.col("len").sum().alias("total_fills"),
            ]
        )
        .with_columns(
            (pl.col("top_labeler_fills") / pl.col("total_fills")).alias("top_labeler_share")
        )
    )

    return {
        "real_mean": real_concentration["top_labeler_share"].mean(),
        "real_median": real_concentration["top_labeler_share"].median(),
        "shuffled_mean": shuffled_concentration["top_labeler_share"].mean(),
        "shuffled_median": shuffled_concentration["top_labeler_share"].median(),
    }


def gate3_90day_share_null(con):
    """Is a beneficiary's tendency toward 90-day fills, a real personal
    trait, or indistinguishable from random chance?"""
    pde_days_supply = con.execute("""
        SELECT DESYNPUF_ID, CAST(DAYS_SUPLY_NUM AS INTEGER) AS days_supply
        FROM raw.pde
        ORDER BY DESYNPUF_ID, PDE_ID
    """).pl()
    pde_days_supply = pde_days_supply.with_columns((pl.col("days_supply") == 90).alias("is_90day"))

    real_90day_share = (
        pde_days_supply.group_by("DESYNPUF_ID")
        .agg([pl.col("is_90day").sum().alias("n_90day"), pl.len().alias("total_fills")])
        .with_columns((pl.col("n_90day") / pl.col("total_fills")).alias("share_90day"))
    )

    shuffled_is_90day = pde_days_supply.with_columns(
        pl.col("is_90day").shuffle(seed=SEED).alias("is_90day")
    )
    shuffled_90day_share = (
        shuffled_is_90day.group_by("DESYNPUF_ID")
        .agg([pl.col("is_90day").sum().alias("n_90day"), pl.len().alias("total_fills")])
        .with_columns((pl.col("n_90day") / pl.col("total_fills")).alias("share_90day"))
    )

    ks_stat, ks_pvalue = stats.ks_2samp(
        real_90day_share["share_90day"].to_numpy(),
        shuffled_90day_share["share_90day"].to_numpy(),
    )

    return {
        "real_mean": real_90day_share["share_90day"].mean(),
        "shuffled_mean": shuffled_90day_share["share_90day"].mean(),
        "real_std": real_90day_share["share_90day"].std(),
        "shuffled_std": shuffled_90day_share["share_90day"].std(),
        "ks_stat": ks_stat,
        "ks_pvalue": ks_pvalue,
    }


def gate4_monthly_plateau_threshold(con):
    """Find the first 2010 month where fills-per-enrolled-beneficiary drops
    below 90% of the 2009 plateau. This sets the usable analysis window."""
    monthly_fills = con.execute("""
        SELECT DATE_TRUNC('month', STRPTIME(SRVC_DT, '%Y%m%d')) AS month,
               COUNT(*) AS n_fills
        FROM raw.pde
        GROUP BY month
        ORDER BY month
    """).pl()

    enrolled_per_year = con.execute("""
        SELECT source_year, COUNT(DISTINCT DESYNPUF_ID) AS n_enrolled
        FROM raw.beneficiary
        GROUP BY source_year
    """).pl()

    monthly_fills = monthly_fills.with_columns(pl.col("month").dt.year().alias("year"))
    monthly_fills = monthly_fills.join(enrolled_per_year, left_on="year", right_on="source_year")
    monthly_fills = monthly_fills.with_columns(
        (pl.col("n_fills") / pl.col("n_enrolled")).alias("fills_per_enrolled")
    )

    plateau_2009 = monthly_fills.filter(pl.col("year") == 2009)["fills_per_enrolled"].mean()
    threshold = 0.90 * plateau_2009

    below_threshold = monthly_fills.filter(
        (pl.col("year") == 2010) & (pl.col("fills_per_enrolled") < threshold)
    ).sort("month")

    first_breach = below_threshold.head(1)

    return {
        "plateau_2009": plateau_2009,
        "threshold": threshold,
        "first_breach_month": first_breach["month"][0] if first_breach.height > 0 else None,
        "first_breach_value": first_breach["fills_per_enrolled"][0]
        if first_breach.height > 0
        else None,
        "dec_2010_value": monthly_fills.filter(pl.col("month") == pl.datetime(2010, 12, 1))[
            "fills_per_enrolled"
        ][0],
    }


def gate5_ndc_directory_lookup():
    """Manual lookup results from the FDA NDC Directory (accessdata.fda.gov),
    checked by hand, not automatable without scraping infrastructure.
    Recorded here for reproducibility of what was checked and found.

    Caveat (per strategy review): the directory only lists currently
    marketed products, so a "no results" finding doesn't prove a labeler
    code was synthesized, it could belong to a company no longer
    operating. Gate 2 (no real person-level clustering signal) is the
    stronger, primary evidence; this gate is illustrative/supporting.
    """
    results = {
        "58016": {"fill_rank": 1, "fills": 611243, "found": False},
        "54868": {"fill_rank": 2, "fills": 164072, "found": False},
        "36987": {"fill_rank": 3, "fills": 121940, "found": False},
        "00247": {"fill_rank": 4, "fills": 105153, "found": False},
        "61392": {"fill_rank": 5, "fills": 97719, "found": False},
        "55289": {
            "fill_rank": 8,
            "fills": 42970,
            "found": True,
            "company": "PD-Rx Pharmaceuticals, Inc. (repackager)",
        },
        "51079": {
            "fill_rank": 10,
            "fills": 41432,
            "found": True,
            "company": "Mylan Institutional Inc.",
        },
    }
    return results


def gate6_test1_days_supply_timing(con):
    """Does a 90-day fill produce a longer gap to the next fill than a
    30-day fill, among low-intensity beneficiaries? Compared against a
    within-person shuffle null."""
    clean_pde = (
        con.execute("""
        SELECT DESYNPUF_ID, PDE_ID, CAST(STRPTIME(SRVC_DT, '%Y%m%d') AS DATE) AS fill_date,
               CAST(DAYS_SUPLY_NUM AS INTEGER) AS days_supply
        FROM raw.pde
        WHERE STRPTIME(SRVC_DT, '%Y%m%d') < DATE '2010-02-01'
    """)
        .pl()
        .sort(["DESYNPUF_ID", "fill_date", "PDE_ID"])
    )

    fill_counts_clean = clean_pde.group_by("DESYNPUF_ID").len().rename({"len": "n_fills"})
    low_intensity_ids = (
        fill_counts_clean.filter(pl.col("n_fills") >= 4)
        .filter(pl.col("n_fills") <= fill_counts_clean["n_fills"].quantile(0.33))["DESYNPUF_ID"]
        .implode()
    )

    low_intensity_pde = clean_pde.filter(pl.col("DESYNPUF_ID").is_in(low_intensity_ids))
    low_intensity_pde = low_intensity_pde.with_columns(
        (pl.col("fill_date").shift(-1).over("DESYNPUF_ID") - pl.col("fill_date"))
        .dt.total_days()
        .alias("gap_to_next")
    )

    real_30 = low_intensity_pde.filter(
        (pl.col("days_supply") == 30) & pl.col("gap_to_next").is_not_null()
    )
    real_90 = low_intensity_pde.filter(
        (pl.col("days_supply") == 90) & pl.col("gap_to_next").is_not_null()
    )
    real_diff = real_90["gap_to_next"].median() - real_30["gap_to_next"].median()

    shuffled = low_intensity_pde.with_columns(
        pl.col("days_supply").shuffle(seed=SEED).over("DESYNPUF_ID").alias("days_supply_shuffled")
    )
    shuf_30 = shuffled.filter(
        (pl.col("days_supply_shuffled") == 30) & pl.col("gap_to_next").is_not_null()
    )
    shuf_90 = shuffled.filter(
        (pl.col("days_supply_shuffled") == 90) & pl.col("gap_to_next").is_not_null()
    )
    shuf_diff = shuf_90["gap_to_next"].median() - shuf_30["gap_to_next"].median()

    return {
        "real_30_median": real_30["gap_to_next"].median(),
        "real_90_median": real_90["gap_to_next"].median(),
        "real_diff": real_diff,
        "shuf_diff": shuf_diff,
    }, clean_pde


def gate6_test2_timing_structure(clean_pde):
    """For each beneficiary, redraw fill dates uniformly within their own
    observation window (keeping fill count and window fixed). Compare real
    vs. redrawn on coefficient of variation of gaps, share with a 60+ day
    gap, and resume-within-90-days rate."""
    rng = np.random.default_rng(SEED)

    clean_fill_dates = (
        clean_pde.group_by("DESYNPUF_ID", maintain_order=True)
        .agg(pl.col("fill_date").sort().alias("dates"))
        .filter(pl.col("dates").list.len() >= 3)
        .sort("DESYNPUF_ID")
    )

    def coeff_of_var(gaps):
        return np.nan if gaps.mean() == 0 else gaps.std() / gaps.mean()

    real_cvs, real_any60, real_resume90 = [], [], []
    redrawn_cvs, redrawn_any60, redrawn_resume90 = [], [], []

    for row in clean_fill_dates.iter_rows(named=True):
        dates_np = np.array(sorted(row["dates"]), dtype="datetime64[D]")
        n = len(dates_np)

        gaps = np.diff(dates_np).astype(int)
        real_cvs.append(coeff_of_var(gaps))
        has60 = np.any(gaps >= 60)
        real_any60.append(has60)
        if has60:
            first60_idx = np.where(gaps >= 60)[0][0]
            real_resume90.append(gaps[first60_idx] <= 90)

        start, end = dates_np[0], dates_np[-1]
        window_days = int((end - start).astype(int))
        if n > 2 and window_days > 0:
            interior = rng.integers(0, window_days + 1, size=n - 2)
            redrawn = np.sort(np.concatenate([[0], interior, [window_days]]))
        else:
            redrawn = np.array([0, window_days])
        rgaps = np.diff(redrawn)
        redrawn_cvs.append(coeff_of_var(rgaps))
        rhas60 = np.any(rgaps >= 60)
        redrawn_any60.append(rhas60)
        if rhas60:
            rfirst60_idx = np.where(rgaps >= 60)[0][0]
            redrawn_resume90.append(rgaps[rfirst60_idx] <= 90)

    return {
        "n_tested": len(real_cvs),
        "real_cv_median": np.nanmedian(real_cvs),
        "redrawn_cv_median": np.nanmedian(redrawn_cvs),
        "real_any60_pct": 100 * np.mean(real_any60),
        "redrawn_any60_pct": 100 * np.mean(redrawn_any60),
        "real_resume90_pct": 100 * np.mean(real_resume90),
        "redrawn_resume90_pct": 100 * np.mean(redrawn_resume90),
    }


def gate6_test3_file_connectivity(con):
    """Spearman correlation of 2008 fill count with chronic-condition
    count and with 2008 inpatient admissions — tests whether PDE is
    meaningfully connected to the rest of the beneficiary record."""
    condition_cols = [
        "SP_ALZHDMTA",
        "SP_CHF",
        "SP_CHRNKIDN",
        "SP_CNCR",
        "SP_COPD",
        "SP_DEPRESSN",
        "SP_DIABETES",
        "SP_ISCHMCHT",
        "SP_OSTEOPRS",
        "SP_RA_OA",
        "SP_STRKETIA",
    ]
    sum_expr = " + ".join([f"CASE WHEN {c} = '1' THEN 1 ELSE 0 END" for c in condition_cols])

    connectivity = con.execute(f"""
        SELECT
            b.DESYNPUF_ID,
            ({sum_expr}) AS n_conditions,
            COUNT(DISTINCT p.PDE_ID) AS n_fills_2008,
            COUNT(DISTINCT i.CLM_ID) AS n_admissions_2008
        FROM raw.beneficiary b
        LEFT JOIN raw.pde p ON b.DESYNPUF_ID = p.DESYNPUF_ID
            AND STRPTIME(p.SRVC_DT, '%Y%m%d') < DATE '2009-01-01'
        LEFT JOIN raw.inpatient i ON b.DESYNPUF_ID = i.DESYNPUF_ID
            AND STRPTIME(i.CLM_FROM_DT, '%Y%m%d') < DATE '2009-01-01'
        WHERE b.source_year = 2008
        GROUP BY b.DESYNPUF_ID, n_conditions
    """).pl()

    spearman_conditions = connectivity.select(
        pl.corr("n_conditions", "n_fills_2008", method="spearman")
    ).item()
    spearman_admissions = connectivity.select(
        pl.corr("n_admissions_2008", "n_fills_2008", method="spearman")
    ).item()

    return {
        "spearman_conditions": spearman_conditions,
        "spearman_admissions": spearman_admissions,
        "passes_threshold": spearman_conditions >= 0.2,
    }


def main():
    con = duckdb.connect(DB_PATH)

    # Gate 1 print block
    print("=" * 60)
    print("GATE 1: Population-wide refill-pair check")
    print("=" * 60)
    g1 = gate1_refill_pairs(con)
    print("Product-code level:")
    print(f"  Total (beneficiary, product) pairs: {g1['product_total_pairs']:,}")
    print(
        f"  Pairs with >=2 fills (a real refill): {g1['product_pairs_with_refill']:,} "
        f"({g1['product_pct_refill']:.2f}%)"
    )
    print("\nLabeler-code level:")
    print(f"  Total (beneficiary, labeler) pairs: {g1['labeler_total_pairs']:,}")
    print(
        f"  Pairs with >=2 fills: {g1['labeler_pairs_with_refill']:,} "
        f"({g1['labeler_pct_refill']:.2f}%)"
    )

    # Gate 2 print block
    print("\n" + "=" * 60)
    print("GATE 2: Labeler concentration vs. shuffle null")
    print("=" * 60)
    g2 = gate2_labeler_concentration_null(con)
    print(f"Real data     — mean: {g2['real_mean']:.4f}, median: {g2['real_median']:.4f}")
    print(f"Shuffled null — mean: {g2['shuffled_mean']:.4f}, median: {g2['shuffled_median']:.4f}")

    # Gate 3 print block
    print("\n" + "=" * 60)
    print("GATE 3: 90-day-supply share vs. shuffle null")
    print("=" * 60)
    g3 = gate3_90day_share_null(con)
    print(f"Real data     — mean: {g3['real_mean']:.4f}, std: {g3['real_std']:.4f}")
    print(f"Shuffled null — mean: {g3['shuffled_mean']:.4f}, std: {g3['shuffled_std']:.4f}")
    print(f"KS statistic: {g3['ks_stat']:.4f}, p-value: {g3['ks_pvalue']:.2e}")

    # Gate 4 print block
    print("\n" + "=" * 60)
    print("GATE 4: Fills-per-enrolled-beneficiary monthly plateau threshold")
    print("=" * 60)
    g4 = gate4_monthly_plateau_threshold(con)
    print(f"2009 plateau (mean fills/enrolled): {g4['plateau_2009']:.3f}")
    print(f"90% threshold: {g4['threshold']:.3f}")
    print(
        f"First 2010 month below threshold: {g4['first_breach_month']} "
        f"({g4['first_breach_value']:.3f})"
    )
    print(
        f"December 2010 value (for reference): {g4['dec_2010_value']:.3f} "
        f"({100*g4['dec_2010_value']/g4['plateau_2009']:.0f}% of plateau)"
    )

    # Gate 5 print block
    print("\n" + "=" * 60)
    print("GATE 5: FDA NDC Directory lookup (manual check, recorded here)")
    print("=" * 60)
    g5 = gate5_ndc_directory_lookup()
    for labeler, info in g5.items():
        status = f"FOUND: {info['company']}" if info["found"] else "NOT FOUND"
        print(f"  {labeler} (rank #{info['fill_rank']}, {info['fills']:,} fills): {status}")

    # Gate 6, Test 1 print block
    print("\n" + "=" * 60)
    print("GATE 6, TEST 1: Days-supply -> next-fill-gap relationship")
    print("=" * 60)
    g6t1, clean_pde = gate6_test1_days_supply_timing(con)
    print(
        f"Real:     30-day median gap {g6t1['real_30_median']:.1f}d, "
        f"90-day median gap {g6t1['real_90_median']:.1f}d, diff {g6t1['real_diff']:.1f}d"
    )
    print(f"Shuffled: diff {g6t1['shuf_diff']:.1f}d")

    # Gate 6, Test 2 print block
    print("\n" + "=" * 60)
    print("GATE 6, TEST 2: Timing structure beyond fill intensity")
    print("=" * 60)
    g6t2 = gate6_test2_timing_structure(clean_pde)
    print(f"Beneficiaries tested: {g6t2['n_tested']:,}")
    print(
        f"CV of gaps       — real: {g6t2['real_cv_median']:.3f}, redrawn: {g6t2['redrawn_cv_median']:.3f}"
    )
    print(
        f"Any 60+ day gap  — real: {g6t2['real_any60_pct']:.1f}%, redrawn: {g6t2['redrawn_any60_pct']:.1f}%"
    )
    print(
        f"Resume within 90d— real: {g6t2['real_resume90_pct']:.1f}%, redrawn: {g6t2['redrawn_resume90_pct']:.1f}%"
    )

    # Gate 6, Test 3 print block
    print("\n" + "=" * 60)
    print("GATE 6, TEST 3: File connectivity")
    print("=" * 60)
    g6t3 = gate6_test3_file_connectivity(con)
    print(f"Spearman rho (fill count, chronic conditions): {g6t3['spearman_conditions']:.3f}")
    print(f"Spearman rho (fill count, inpatient admissions): {g6t3['spearman_admissions']:.3f}")
    print(f"Threshold 0.2: {'PASS' if g6t3['passes_threshold'] else 'FAIL'}")

    print("\n" + "=" * 60)
    print("FIDELITY AUDIT COMPLETE")
    print("=" * 60)

    con.close()


if __name__ == "__main__":
    main()
