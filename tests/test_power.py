"""
Round-trip consistency, monotonicity, and two published-value sanity
checks for experiments/simulation/power.py.
"""

import pytest

from experiments.simulation.power import (
    mde_continuous,
    n_for_continuous,
    n_for_proportions,
    power_for,
)


class TestRoundTrip:
    def test_continuous_round_trip_recovers_80_percent_power(self):
        n = n_for_continuous(sd=1.556, mde=0.25)
        achieved = power_for(effect=0.25, n_per_arm=n, sd=1.556)
        assert achieved == pytest.approx(0.80, abs=0.01)

    def test_proportions_round_trip_recovers_80_percent_power(self):
        n = n_for_proportions(baseline_p=0.089, mde=0.02)
        achieved = power_for(effect=0.02, n_per_arm=n, baseline_p=0.089)
        assert achieved == pytest.approx(0.80, abs=0.01)

    def test_continuous_round_trip_holds_at_unequal_allocation(self):
        n = n_for_continuous(sd=1.556, mde=0.25, allocation=0.3)
        achieved = power_for(effect=0.25, n_per_arm=n, sd=1.556, allocation=0.3)
        assert achieved == pytest.approx(0.80, abs=0.01)


class TestMonotonicity:
    def test_mde_continuous_shrinks_as_n_grows(self):
        assert mde_continuous(sd=1.556, n_per_arm=5000) < mde_continuous(sd=1.556, n_per_arm=500)

    def test_mde_continuous_grows_with_sd(self):
        assert mde_continuous(sd=2.0, n_per_arm=1000) > mde_continuous(sd=1.0, n_per_arm=1000)

    def test_n_for_continuous_shrinks_as_mde_grows(self):
        assert n_for_continuous(sd=1.556, mde=0.5) < n_for_continuous(sd=1.556, mde=0.1)

    def test_power_for_grows_with_n(self):
        assert power_for(effect=0.2, n_per_arm=5000, sd=1.556) > power_for(
            effect=0.2, n_per_arm=500, sd=1.556
        )

    def test_mde_worsens_away_from_equal_allocation(self):
        equal = mde_continuous(sd=1.556, n_per_arm=1000, allocation=0.5)
        unequal = mde_continuous(sd=1.556, n_per_arm=1000, allocation=0.2)
        assert unequal > equal


class TestPublishedValues:
    def test_matches_textbook_two_sample_n(self):
        # d=0.5, alpha=.05 two-sided, power=.80, equal allocation -> ~64/arm
        n = n_for_continuous(sd=1.0, mde=0.5)
        assert n == pytest.approx(64, abs=2)

    def test_matches_textbook_two_proportion_n(self):
        # baseline 50%, 10pp absolute shift, alpha=.05, power=.80 -> ~390-400/arm
        n = n_for_proportions(baseline_p=0.5, mde=0.10)
        assert n == pytest.approx(393, abs=10)
