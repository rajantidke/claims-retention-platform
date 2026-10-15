"""
Bootstrap Type-I validation and power-curve comparison for Module B.

The A/A test is bootstrap-resampled from the real post-period active-
months distribution (and its <=2-month binary indicator), not simulated
from a normal distribution - the metric is bounded 0-6, discrete, and
not bell-shaped, so whether a two-sample test holds nominal size on
this shape at this project's sample sizes is an open question, not
an assumption. I have been rolling my eyes at myself for thinking of this
whole idea of combining product data science methodologies on RWE data myself
right about now. Anyway.

Three sample sizes per metric: SMALL/MEDIUM/FULL. The binary test uses a
pooled two-proportion z-test, which has a known small-sample failure
mode at a low baseline rate -- ours is 8.92%, so SMALL (200/arm) is
exactly where that mode would show up if it exists here.

The interpretation table is fixed before any replicate is run:
  - FPR within the binomial CI of 5% at all three sizes -> nominal, report and move on
  - FPR outside the CI at SMALL only -> real small-sample finding, report the floor
  - FPR outside the CI at FULL -> harness bug, not a test property; stop
  - empirical power vs. analytic power differs by >3pp anywhere -> investigate before publishing;
    investigation may conclude the gap is expected (e.g. pooled-vs-unpooled variance in the binary
    test is conservative by design, not a bug) rather than requiring a fix
"""

import json
from pathlib import Path

import numpy as np
from scipy.stats import norm, ttest_ind

from experiments.simulation.power import power_for

ALPHA = 0.05
N_REPLICATES = 10_000
SAMPLE_SIZES = {"small": 200, "medium": 2000, "full": None}  # full resolved at call time
POWER_DEVIATION_BAR_PP = 3.0
RESULTS_PATH = Path("reports/harness_validation.json")


def binomial_ci(observed_rate, n_replicates, z=1.96):
    """Normal-approximation CI on an observed proportion over
    n_replicates draws -- used to judge whether an empirical FPR is
    consistent with the nominal alpha."""
    se = np.sqrt(observed_rate * (1 - observed_rate) / n_replicates)
    return observed_rate - z * se, observed_rate + z * se


def bootstrap_aa_continuous(values, n_per_arm, n_replicates=N_REPLICATES, alpha=ALPHA, seed=7):
    """Resample two arms of size n_per_arm with replacement from `values`
    (the real distribution), run a two-sample t-test, repeat
    n_replicates times. The null is true by construction (both arms
    drawn from the same pool); the empirical rejection rate is the
    empirical Type-I error."""
    rng = np.random.default_rng(seed)
    values = np.asarray(values)
    rejections = 0

    for _ in range(n_replicates):
        a = rng.choice(values, size=n_per_arm, replace=True)
        b = rng.choice(values, size=n_per_arm, replace=True)
        _, p = ttest_ind(a, b)
        if p < alpha:
            rejections += 1

    fpr = rejections / n_replicates
    ci = binomial_ci(fpr, n_replicates)
    return {"n_per_arm": n_per_arm, "n_replicates": n_replicates, "fpr": fpr, "fpr_ci": ci}


def _two_proportion_ztest(a, b):
    """Pooled two-proportion z-test. The pooled-variance normal
    approximation this relies on is known to degrade when the expected
    count in either arm (n*p) is small -- exactly the regime this
    project's low baseline rate (8.92%) and SMALL sample size (200/arm)
    can land in."""
    n1, n2 = len(a), len(b)
    p1, p2 = a.mean(), b.mean()
    p_pool = (a.sum() + b.sum()) / (n1 + n2)
    se = np.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = (p1 - p2) / se
    return 2 * (1 - norm.cdf(abs(z)))


def bootstrap_aa_binary(values, n_per_arm, n_replicates=N_REPLICATES, alpha=ALPHA, seed=7):
    """Same bootstrap design as bootstrap_aa_continuous, using the
    pooled two-proportion z-test instead of the t-test."""
    rng = np.random.default_rng(seed)
    values = np.asarray(values)
    rejections = 0

    for _ in range(n_replicates):
        a = rng.choice(values, size=n_per_arm, replace=True)
        b = rng.choice(values, size=n_per_arm, replace=True)
        p = _two_proportion_ztest(a, b)
        if p < alpha:
            rejections += 1

    fpr = rejections / n_replicates
    ci = binomial_ci(fpr, n_replicates)
    return {"n_per_arm": n_per_arm, "n_replicates": n_replicates, "fpr": fpr, "fpr_ci": ci}


def run_aa_sweep(
    continuous_values, binary_values, full_n_per_arm, n_replicates=N_REPLICATES, seed=7
):
    """Runs both bootstrap A/A tests at SMALL (200), MEDIUM (2000), and
    FULL (the real eligible population's n_per_arm) sample sizes, and
    applies the pre-committed interpretation table."""
    sizes = {"small": 200, "medium": 2000, "full": full_n_per_arm}

    continuous_results = {
        label: bootstrap_aa_continuous(continuous_values, n, n_replicates=n_replicates, seed=seed)
        for label, n in sizes.items()
    }
    binary_results = {
        label: bootstrap_aa_binary(binary_values, n, n_replicates=n_replicates, seed=seed)
        for label, n in sizes.items()
    }

    def interpret(results):
        nominal_lo, nominal_hi = binomial_ci(ALPHA, n_replicates)
        flags = {label: not (nominal_lo <= r["fpr"] <= nominal_hi) for label, r in results.items()}
        if not any(flags.values()):
            return "nominal_at_all_sizes"
        if flags["full"]:
            return "harness_bug_suspected"
        if flags["small"] and not flags["medium"]:
            return "small_sample_failure_below_medium"
        if flags["small"] or flags["medium"]:
            return "small_sample_failure"
        return "nominal_at_all_sizes"

    return {
        "continuous": {**continuous_results, "interpretation": interpret(continuous_results)},
        "binary": {**binary_results, "interpretation": interpret(binary_results)},
        "nominal_ci": binomial_ci(ALPHA, n_replicates),
    }


def power_curve(
    continuous_values,
    binary_values,
    continuous_n_per_arm,
    binary_n_per_arm,
    continuous_effects,
    binary_effects,
    continuous_sd,
    binary_baseline_p,
    n_replicates=N_REPLICATES,
    alpha=ALPHA,
    seed=7,
):
    """Empirical power (fraction of bootstrap replicates rejecting)
    against analytic power (power_for), at a grid of effect sizes, for
    both metrics. Injects each effect additively into one resampled
    arm before testing."""
    rng = np.random.default_rng(seed)

    def empirical_power_continuous(effect, n_per_arm):
        rejections = 0
        for _ in range(n_replicates):
            control = rng.choice(continuous_values, size=n_per_arm, replace=True)
            treatment = rng.choice(continuous_values, size=n_per_arm, replace=True) + effect
            _, p = ttest_ind(control, treatment)
            if p < alpha:
                rejections += 1
        return rejections / n_replicates

    def empirical_power_binary(effect, n_per_arm):
        rejections = 0
        flip_prob = effect / (1 - binary_baseline_p)
        for _ in range(n_replicates):
            control = rng.choice(binary_values, size=n_per_arm, replace=True)
            treatment_base = rng.choice(binary_values, size=n_per_arm, replace=True)
            flip_mask = (rng.random(n_per_arm) < flip_prob) & (treatment_base == 0)
            treatment = treatment_base.copy()
            treatment[flip_mask] = 1
            p = _two_proportion_ztest(control, treatment)
            if p < alpha:
                rejections += 1
        return rejections / n_replicates

    continuous_curve = []
    for effect in continuous_effects:
        empirical = empirical_power_continuous(effect, continuous_n_per_arm)
        analytic = power_for(
            effect=effect, n_per_arm=continuous_n_per_arm, sd=continuous_sd, alpha=alpha
        )
        continuous_curve.append(
            {
                "effect": effect,
                "empirical_power": empirical,
                "analytic_power": analytic,
                "deviation_pp": 100 * (empirical - analytic),
            }
        )

    binary_curve = []
    for effect in binary_effects:
        empirical = empirical_power_binary(effect, binary_n_per_arm)
        analytic = power_for(
            effect=effect, n_per_arm=binary_n_per_arm, baseline_p=binary_baseline_p, alpha=alpha
        )
        binary_curve.append(
            {
                "effect": effect,
                "empirical_power": empirical,
                "analytic_power": analytic,
                "deviation_pp": 100 * (empirical - analytic),
            }
        )

    max_deviation = max(
        abs(row["deviation_pp"]) for row in continuous_curve + binary_curve if row["effect"] != 0
    )

    return {
        "continuous_n_per_arm": continuous_n_per_arm,
        "binary_n_per_arm": binary_n_per_arm,
        "continuous_curve": continuous_curve,
        "binary_curve": binary_curve,
        "max_abs_deviation_pp": max_deviation,
        "flagged_for_investigation": max_deviation > POWER_DEVIATION_BAR_PP,
    }


def run_and_save(con):
    from experiments.simulation.baseline import compute_baseline_parameters, load_population

    population = load_population(con)
    continuous_values = population["post_active_months"].to_numpy().astype(np.float64)
    binary_values = (population["post_active_months"] <= 2).to_numpy().astype(np.int64)

    params = compute_baseline_parameters(population)
    full_n_per_arm = params["eligible_population"] // 2

    aa_results = run_aa_sweep(continuous_values, binary_values, full_n_per_arm=full_n_per_arm)

    curve = power_curve(
        continuous_values,
        binary_values,
        continuous_n_per_arm=609,  # Part 2: n for a 0.25-month lift
        binary_n_per_arm=3189,  # Part 2: n for a 2pp reduction
        continuous_effects=[0, 0.1, 0.2, 0.25, 0.35, 0.5],
        binary_effects=[0, 0.01, 0.02, 0.03, 0.05],
        continuous_sd=params["sd_post_active_months"],
        binary_baseline_p=params["baseline_le2_active_months_rate"],
    )

    output_path = RESULTS_PATH
    existing = json.loads(output_path.read_text()) if output_path.exists() else {}
    existing["type1_validation"] = aa_results
    existing["power_curve"] = curve
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(json.dumps(existing, indent=2, default=str))

    return aa_results, curve


if __name__ == "__main__":
    import duckdb

    con = duckdb.connect("data/claims.duckdb", read_only=True)
    aa_results, curve = run_and_save(con)

    print("=== A/A TYPE-I VALIDATION ===")
    for metric in ("continuous", "binary"):
        print(f"\n{metric}:")
        for label in ("small", "medium", "full"):
            r = aa_results[metric][label]
            print(f"  {label} (n={r['n_per_arm']}): FPR {r['fpr']:.4f}, CI {r['fpr_ci']}")
        print(f"  interpretation: {aa_results[metric]['interpretation']}")

    print("\n=== POWER CURVE ===")
    print(f"max abs deviation: {curve['max_abs_deviation_pp']:.2f}pp")
    print(f"flagged for investigation: {curve['flagged_for_investigation']}")
    con.close()
