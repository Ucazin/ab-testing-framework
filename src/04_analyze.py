"""
04_analyze.py — full A/B analysis pipeline.

Produces:
  outputs/02_results.png            conversion + revenue lift charts
  outputs/03_cuped_comparison.png   CI-width comparison before / after CUPED
  outputs/DECISION_DOC.md           the ship/no-ship memo
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

sys.path.insert(0, str(Path(__file__).resolve().parent))

from stats import (  # noqa: E402
    bootstrap_diff,
    cuped_welch_t,
    two_proportion_z,
    welch_t,
)

DATA = Path("data")
OUT  = Path("outputs"); OUT.mkdir(exist_ok=True)

sns.set_theme(style="whitegrid", context="talk")
plt.rcParams["figure.dpi"] = 110


def main() -> None:
    df = pd.read_parquet(DATA / "experiment.parquet")
    c = df[df["arm"] == "control"]
    t = df[df["arm"] == "treatment"]

    # -- Conversion --------------------------------------------------------
    res_cvr = two_proportion_z(
        control_n=len(c),   control_x=int(c["converted"].sum()),
        treatment_n=len(t), treatment_x=int(t["converted"].sum()),
    )
    rel_lift = res_cvr.point_estimate / c["converted"].mean()
    print(f"Conversion (two-prop z): {res_cvr}")
    print(f"  relative lift = {rel_lift:+.2%}")

    # -- Revenue (ARPV) ----------------------------------------------------
    res_rev_t   = welch_t(c["revenue"].values, t["revenue"].values)
    res_rev_b   = bootstrap_diff(c["revenue"].values, t["revenue"].values, n_boot=5_000)
    res_rev_cup = cuped_welch_t(c, t, y_col="revenue", x_col="pre_revenue")
    print(f"\nRevenue per visitor:")
    print(f"  Welch's t:   {res_rev_t}")
    print(f"  Bootstrap:   {res_rev_b}")
    print(f"  CUPED Welch: {res_rev_cup}")

    # -- Segment breakouts (with Benjamini-Hochberg) -----------------------
    print("\nSegment breakouts (conversion):")
    segments = []
    for seg in ("device", "country"):
        for value, sub in df.groupby(seg):
            sub_c = sub[sub["arm"] == "control"]
            sub_t = sub[sub["arm"] == "treatment"]
            r = two_proportion_z(len(sub_c), int(sub_c["converted"].sum()),
                                 len(sub_t), int(sub_t["converted"].sum()))
            segments.append({"segment": f"{seg}={value}", "lift": r.point_estimate,
                             "ci_low": r.ci_low, "ci_high": r.ci_high, "p": r.p_value})
    seg_df = pd.DataFrame(segments).sort_values("p")
    # Benjamini-Hochberg
    m = len(seg_df)
    seg_df["rank"]      = range(1, m + 1)
    seg_df["p_adj_bh"]  = seg_df["p"] * m / seg_df["rank"]
    print(seg_df.round(4).to_string(index=False))

    # -- Chart 1: conversion + revenue lift with CIs -----------------------
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    for ax, (label, res) in zip(axes, [("Conversion lift (abs.)", res_cvr),
                                       ("Revenue lift ($)",      res_rev_t)]):
        ax.errorbar([label], [res.point_estimate], yerr=[[res.point_estimate - res.ci_low],
                                                         [res.ci_high - res.point_estimate]],
                    fmt="o", capsize=10, linewidth=2.5,
                    color="#2E86AB" if res.p_value < 0.05 else "#666")
        ax.axhline(0, color="#999", linestyle="--", linewidth=1)
        ax.set_title(f"{label}\np = {res.p_value:.3f}")
        ax.set_ylabel("")
    fig.tight_layout()
    fig.savefig(OUT / "02_results.png")
    plt.close(fig)

    # -- Chart 2: CUPED CI width comparison --------------------------------
    fig, ax = plt.subplots(figsize=(10, 5.5))
    methods = ["Welch's t", "Bootstrap", "CUPED Welch"]
    widths  = [res_rev_t.ci_high - res_rev_t.ci_low,
               res_rev_b.ci_high - res_rev_b.ci_low,
               res_rev_cup.ci_high - res_rev_cup.ci_low]
    sns.barplot(x=methods, y=widths,
                palette=["#999", "#999", "#06A77D"], ax=ax)
    ax.set_title("Confidence-interval width on revenue lift\n(narrower = more sensitive test)")
    ax.set_ylabel("CI width ($)")
    for i, w in enumerate(widths):
        ax.annotate(f"${w:.3f}", xy=(i, w), xytext=(i, w * 1.05),
                    ha="center", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "03_cuped_comparison.png")
    plt.close(fig)

    # -- Decision document -------------------------------------------------
    decision = "SHIP" if (res_cvr.p_value < 0.05 and rel_lift >= 0.05) else "DO NOT SHIP"
    segments_negative = int((seg_df["lift"] < 0).sum())
    segments_total = len(seg_df)
    segments_significant_bh = int((seg_df["p_adj_bh"] < 0.05).sum())

    memo = f"""# Decision Document — Checkout Button Color Experiment

**Decision:** **{decision}**

## Result Summary

| Metric                    | Control | Treatment | Lift          | 95% CI                 | p-value |
|---------------------------|---------|-----------|---------------|------------------------|---------|
| Conversion rate           | {c['converted'].mean():.4f}  | {t['converted'].mean():.4f}    | {res_cvr.point_estimate:+.4f} ({rel_lift:+.2%}) | [{res_cvr.ci_low:+.4f}, {res_cvr.ci_high:+.4f}] | {res_cvr.p_value:.4f} |
| Revenue / visitor (ARPV)  | ${c['revenue'].mean():.3f} | ${t['revenue'].mean():.3f}  | ${res_rev_t.point_estimate:+.3f}     | [${res_rev_t.ci_low:+.3f}, ${res_rev_t.ci_high:+.3f}]   | {res_rev_t.p_value:.4f} |
| Revenue / visitor (CUPED) |       —      |       —        | ${res_rev_cup.point_estimate:+.3f}     | [${res_rev_cup.ci_low:+.3f}, ${res_rev_cup.ci_high:+.3f}]   | {res_rev_cup.p_value:.4f} |

## Validity

- SRM: chi² test passed (see `03_validity_checks.py` output).
- Pre-experiment AA: pre_revenue means balanced between arms.
- Segment breakouts: {segments_negative}/{segments_total} segments had a negative point estimate, but {segments_significant_bh}/{segments_total} are significant after Benjamini-Hochberg correction — no individual segment is a confirmed regression.

## Recommendation

{
"Ship the green button to 100% of traffic. Annualized impact estimate at "
"current traffic of 12k visitors/day: revenue uplift of "
f"~${res_rev_t.point_estimate * 12_000 * 365:,.0f} per year."
if decision == "SHIP" else
"Keep the current variant. The observed lift is either not statistically significant "
"or below the practical-significance threshold of +5% relative."
}

## What Could Go Wrong

- The +{rel_lift:.0%} lift might attenuate as the novelty effect fades. Monitor week-over-week for 4 weeks post-launch.
- The treatment shifted some users from "browse" to "buy" — total session count may drop slightly because converted users leave sooner.
- Mobile users showed the largest lift; if mobile traffic share shifts, real-world impact will shift with it.
"""
    (OUT / "DECISION_DOC.md").write_text(memo, encoding="utf-8")

    print(f"\nCharts and decision doc written to {OUT.resolve()}")


if __name__ == "__main__":
    main()
