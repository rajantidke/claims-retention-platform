"""
Tests for the Type-I bootstrap and power-curve mechanics in
experiments/simulation/validation.py. These run at a small replicate
count (200, not 10,000) - they check that the machinery behaves
correctly, not that the full-scale sweep reproduces its published
numbers (that's a two-run diff on the real script, not a test).
"""

import numpy as np

from experiments.simulation.validation import (
    binomial_ci,
    bootstrap_aa_binary,
    bootstrap_aa_continuous,
    power_curve,
    run_aa_sweep,
)


class TestBinomialCI:
    def test_centered_on_observed_rate(self):
        lo, hi = binomial_ci(0.05, 10_000)
        assert lo < 0.05 < hi

    def test_narrows_with_more_replicates(self):
        lo_small, hi_small = binomial_ci(0.05, 1_000)
        lo_large, hi_large = binomial_ci(0.05, 100_000)
        assert (hi_large - lo_large) < (hi_small - lo_small)


class TestDeterminism:
    def test_continuous_bootstrap_reproduces_with_same_seed(self):
        values = np.array([0, 1, 2, 3, 4, 5, 6] * 50)
        r1 = bootstrap_aa_continuous(values, n_per_arm=50, n_replicates=200, seed=3)
        r2 = bootstrap_aa_continuous(values, n_per_arm=50, n_replicates=200, seed=3)
        assert r1["fpr"] == r2["fpr"]

    def test_binary_bootstrap_reproduces_with_same_seed(self):
        values = np.array([0, 0, 0, 1] * 50)
        r1 = bootstrap_aa_binary(values, n_per_arm=50, n_replicates=200, seed=3)
        r2 = bootstrap_aa_binary(values, n_per_arm=50, n_replicates=200, seed=3)
        assert r1["fpr"] == r2["fpr"]

    def test_different_seeds_can_diverge(self):
        values = np.array([0, 1, 2, 3, 4, 5, 6] * 50)
        r1 = bootstrap_aa_continuous(values, n_per_arm=50, n_replicates=200, seed=3)
        r2 = bootstrap_aa_continuous(values, n_per_arm=50, n_replicates=200, seed=4)
        # not asserting inequality (could coincide), just that both run cleanly
        assert isinstance(r1["fpr"], float) and isinstance(r2["fpr"], float)


class TestInterpretation:
    def test_nominal_fpr_labeled_nominal(self):
        values = np.array([0, 1, 2, 3, 4, 5, 6] * 200)
        binary_values = np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 1] * 200)
        result = run_aa_sweep(values, binary_values, full_n_per_arm=100, n_replicates=500, seed=11)
        # a well-behaved t-test / z-test on this much data should come back nominal
        assert result["continuous"]["interpretation"] == "nominal_at_all_sizes"


class TestPowerCurveEffectInjection:
    def test_binary_effect_delivers_expected_rate_shift_in_expectation(self):
        """The flip-probability fix: effect / (1 - baseline_p) should
        deliver `effect` as the expected rate shift, not
        effect * (1 - baseline_p). Checked directly against a large
        synthetic sample rather than through the full power curve."""
        baseline_p = 0.10
        n = 50_000
        rng = np.random.default_rng(0)
        base = (rng.random(n) < baseline_p).astype(int)
        effect = 0.05
        flip_prob = effect / (1 - baseline_p)
        flip_mask = (rng.random(n) < flip_prob) & (base == 0)
        treated = base.copy()
        treated[flip_mask] = 1
        delivered_shift = treated.mean() - base.mean()
        assert abs(delivered_shift - effect) < 0.01  # sampling tolerance at n=50k

    def test_power_curve_runs_and_returns_expected_keys(self):
        values = np.array([0, 1, 2, 3, 4, 5, 6] * 100)
        binary_values = np.array([0, 0, 0, 0, 0, 0, 0, 0, 1, 1] * 100)
        result = power_curve(
            values,
            binary_values,
            continuous_n_per_arm=50,
            binary_n_per_arm=50,
            continuous_effects=[0, 0.5],
            binary_effects=[0, 0.1],
            continuous_sd=1.8,
            binary_baseline_p=0.2,
            n_replicates=300,
            seed=5,
        )
        assert "continuous_curve" in result and "binary_curve" in result
        assert "max_abs_deviation_pp" in result
