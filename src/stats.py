"""
stats.py — reusable statistical primitives for A/B test analysis.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportions_ztest


@dataclass
class TestResult:
    point_estimate: float
    ci_low: float
    ci_high: float
    p_value: float
    note: str = ""

    def __str__(self) -> str:
        return (f"  point = {self.point_estimate:+.4f}   "
                f"95% CI [{self.ci_low:+.4f}, {self.ci_high:+.4f}]   "
                f"p = {self.p_value:.4f}  {self.note}")


# ---------------------------------------------------------------------------
# Power analysis
# ---------------------------------------------------------------------------

def sample_size_two_proportions(p_baseline: float, relative_lift: float,
                                 alpha: float = 0.05, power: float = 0.80,
                                 two_sided: bool = True) -> int:
    """Sample size per arm for detecting a relative lift in a proportion."""
    p_treatment = p_baseline * (1 + relative_lift)
    pooled = (p_baseline + p_treatment) / 2
    # Cohen's h effect size
    h = 2 * (np.arcsin(np.sqrt(p_treatment)) - np.arcsin(np.sqrt(p_baseline)))
    analysis = NormalIndPower()
    n = analysis.solve_power(effect_size=abs(h),
                             alpha=alpha,
                             power=power,
                             alternative="two-sided" if two_sided else "larger")
    return int(np.ceil(n))


# ---------------------------------------------------------------------------
# Two-proportion z-test
# ---------------------------------------------------------------------------

def two_proportion_z(control_n: int, control_x: int,
                     treatment_n: int, treatment_x: int,
                     alpha: float = 0.05) -> TestResult:
    counts   = np.array([treatment_x, control_x])
    nobs     = np.array([treatment_n, control_n])
    stat, p  = proportions_ztest(counts, nobs)
    p1 = treatment_x / treatment_n
    p0 = control_x   / control_n
    diff = p1 - p0
    # Wald CI
    se = np.sqrt(p1*(1-p1)/treatment_n + p0*(1-p0)/control_n)
    z = stats.norm.ppf(1 - alpha/2)
    return TestResult(diff, diff - z*se, diff + z*se, p)


# ---------------------------------------------------------------------------
# Welch's t-test (continuous outcomes)
# ---------------------------------------------------------------------------

def welch_t(control: np.ndarray, treatment: np.ndarray,
            alpha: float = 0.05) -> TestResult:
    res  = stats.ttest_ind(treatment, control, equal_var=False)
    diff = treatment.mean() - control.mean()
    se   = np.sqrt(treatment.var(ddof=1) / len(treatment)
                   + control.var(ddof=1)   / len(control))
    df_w = (se**4) / (
        (treatment.var(ddof=1)/len(treatment))**2 / (len(treatment)-1)
        + (control.var(ddof=1)/len(control))**2   / (len(control)-1)
    )
    t = stats.t.ppf(1 - alpha/2, df=df_w)
    return TestResult(diff, diff - t*se, diff + t*se, float(res.pvalue))


# ---------------------------------------------------------------------------
# Bootstrap CI for difference of means
# ---------------------------------------------------------------------------

def bootstrap_diff(control: np.ndarray, treatment: np.ndarray,
                   n_boot: int = 10_000, alpha: float = 0.05,
                   seed: int = 42) -> TestResult:
    rng = np.random.default_rng(seed)
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        c = rng.choice(control,   size=len(control),   replace=True)
        t = rng.choice(treatment, size=len(treatment), replace=True)
        diffs[i] = t.mean() - c.mean()
    lo, hi = np.quantile(diffs, [alpha/2, 1 - alpha/2])
    p = (np.abs(diffs - diffs.mean()) >= abs(treatment.mean() - control.mean())).mean()
    return TestResult(treatment.mean() - control.mean(), lo, hi, p,
                      note=f"({n_boot:,} bootstrap resamples)")


# ---------------------------------------------------------------------------
# CUPED variance reduction
# ---------------------------------------------------------------------------

def cuped_adjust(y: np.ndarray, x: np.ndarray) -> tuple[np.ndarray, float]:
    """
    Variance reduction with a single covariate x (e.g. pre-period revenue).

    Returns (y_adjusted, theta) where y_adjusted = y - theta * (x - mean(x)).
    """
    x = np.asarray(x); y = np.asarray(y)
    theta = float(np.cov(y, x, ddof=1)[0, 1] / np.var(x, ddof=1))
    return y - theta * (x - x.mean()), theta


def cuped_welch_t(control: pd.DataFrame, treatment: pd.DataFrame,
                  y_col: str, x_col: str, alpha: float = 0.05) -> TestResult:
    """Welch's t-test on CUPED-adjusted y."""
    all_x   = np.concatenate([control[x_col].values, treatment[x_col].values])
    all_y   = np.concatenate([control[y_col].values, treatment[y_col].values])
    _, theta = cuped_adjust(all_y, all_x)

    c_adj = control[y_col].values   - theta * (control[x_col].values   - all_x.mean())
    t_adj = treatment[y_col].values - theta * (treatment[x_col].values - all_x.mean())

    res = welch_t(c_adj, t_adj, alpha=alpha)
    res.note = f"(CUPED, theta = {theta:.3f})"
    return res


# ---------------------------------------------------------------------------
# SRM check
# ---------------------------------------------------------------------------

def srm_check(control_n: int, treatment_n: int, planned_split: float = 0.5,
              alpha: float = 0.01) -> tuple[bool, float]:
    """Chi-square test for sample-ratio mismatch. Returns (is_clean, p_value)."""
    observed = np.array([control_n, treatment_n])
    expected = np.array([
        (control_n + treatment_n) * (1 - planned_split),
        (control_n + treatment_n) * planned_split,
    ])
    chi2 = ((observed - expected) ** 2 / expected).sum()
    p = 1 - stats.chi2.cdf(chi2, df=1)
    return (p > alpha, float(p))
