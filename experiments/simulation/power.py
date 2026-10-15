"""
Power / MDE calculator for Module B.

Solves for n, power, or effect given the other two, for both the
continuous metric (post-period active months, 0-6) and the binary
metric (<=2 active months of 6), at a fixed alpha, with support for
unequal allocation between arms.

`n_per_arm` means N/2 throughout - total sample size regardless of how
`allocation` actually splits it - so the parameter keeps one fixed
meaning whether the split is 50/50 or not. Variance is scaled by
1/(k*(1-k)) where k=allocation; this is exactly 4 at k=0.5, which is why
the formulas below reduce to the equal-allocation case there.

Continuous functions take an SD measured directly from
experiments/simulation/baseline.py, not an assumed one.
"""

import math

from scipy.stats import norm


def _z_scores(alpha, power):
    z_alpha2 = norm.ppf(1 - alpha / 2)
    z_power = norm.ppf(power)
    return z_alpha2, z_power


def _variance_inflation(allocation):
    k = allocation
    if not 0 < k < 1:
        raise ValueError(f"allocation must be in (0, 1), got {k}")
    return 1.0 / (k * (1 - k))


def mde_continuous(sd, n_per_arm, alpha=0.05, power=0.80, allocation=0.5):
    """MDE in raw units (active months) at the given n_per_arm, SD,
    alpha, power, and allocation."""
    z_alpha2, z_power = _z_scores(alpha, power)
    vif = _variance_inflation(allocation)
    se = sd * math.sqrt(vif / (2 * n_per_arm))
    return (z_alpha2 + z_power) * se


def n_for_continuous(sd, mde, alpha=0.05, power=0.80, allocation=0.5):
    """n_per_arm required to detect `mde` at the given SD, alpha,
    power, and allocation."""
    z_alpha2, z_power = _z_scores(alpha, power)
    vif = _variance_inflation(allocation)
    n = (z_alpha2 + z_power) ** 2 * sd**2 * vif / (2 * mde**2)
    return math.ceil(n)


def mde_proportions(baseline_p, n_per_arm, alpha=0.05, power=0.80, allocation=0.5):
    """MDE as an absolute proportion shift at the given n_per_arm,
    using baseline_p's variance for both arms (the counterfactual rate
    isn't known at MDE-computation time)."""
    z_alpha2, z_power = _z_scores(alpha, power)
    vif = _variance_inflation(allocation)
    var = baseline_p * (1 - baseline_p)
    se = math.sqrt(var * vif / (2 * n_per_arm))
    return (z_alpha2 + z_power) * se


def n_for_proportions(baseline_p, mde, alpha=0.05, power=0.80, allocation=0.5):
    """n_per_arm required to detect an absolute shift of `mde` away
    from baseline_p."""
    z_alpha2, z_power = _z_scores(alpha, power)
    vif = _variance_inflation(allocation)
    var = baseline_p * (1 - baseline_p)
    n = (z_alpha2 + z_power) ** 2 * var * vif / (2 * mde**2)
    return math.ceil(n)


def power_for(effect, n_per_arm, alpha=0.05, allocation=0.5, sd=None, baseline_p=None):
    """Achieved power for a given effect and n_per_arm. Pass exactly
    one of sd (continuous) or baseline_p (binary)."""
    if (sd is None) == (baseline_p is None):
        raise ValueError("pass exactly one of sd or baseline_p")

    z_alpha2, _ = _z_scores(alpha, power=0.80)
    vif = _variance_inflation(allocation)

    if sd is not None:
        se = sd * math.sqrt(vif / (2 * n_per_arm))
    else:
        var = baseline_p * (1 - baseline_p)
        se = math.sqrt(var * vif / (2 * n_per_arm))

    z_power = effect / se - z_alpha2
    return norm.cdf(z_power)
