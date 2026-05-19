"""
01_design.py — pre-experiment sample size + duration calculator.

Writes outputs/01_design_summary.txt with the planned design.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from stats import sample_size_two_proportions  # noqa: E402

OUT = Path("outputs"); OUT.mkdir(exist_ok=True)


def main() -> None:
    # ------------ scenario assumptions ------------
    baseline_cvr        = 0.050     # 5.0% conversion rate today
    smallest_effect_pct = 0.08      # we care about a +8% relative lift
    alpha               = 0.05      # two-sided
    power               = 0.80
    daily_visitors      = 12_000    # eligible visitors per day, split 50/50
    # ------------------------------------------------

    n_per_arm = sample_size_two_proportions(baseline_cvr, smallest_effect_pct,
                                            alpha=alpha, power=power)
    total_n   = 2 * n_per_arm
    days      = total_n / daily_visitors

    summary = f"""\
A/B Test Pre-Experiment Design
==============================

Hypothesis
    The new checkout-button variant will lift conversion-to-purchase by
    at least +{smallest_effect_pct:.0%} (relative) over baseline.

Inputs
    Baseline conversion rate (control)   :  {baseline_cvr:.2%}
    Smallest detectable relative lift    :  +{smallest_effect_pct:.0%}
    Implied treatment conversion rate    :  {baseline_cvr * (1 + smallest_effect_pct):.4f}
    Significance level (alpha, 2-sided)  :  {alpha}
    Statistical power (1 - beta)         :  {power}

Required sample size
    Per arm                              :  {n_per_arm:,} visitors
    Total                                :  {total_n:,} visitors

Traffic and duration
    Eligible visitors / day              :  {daily_visitors:,}
    Required days to fully power test    :  {days:.1f}

Guardrail metrics (must not regress)
    - Average revenue per visitor (ARPV)
    - Page-load time
    - Cart-abandonment rate (anything that signals confusion from the new variant)

Stopping rules
    - Hard stop at day {round(days)+1} regardless of significance.
    - No peeking before day {round(days/2)}.
    - SRM check at day 2: if chi-square p < 0.01, pause and investigate.
"""
    out_file = OUT / "01_design_summary.txt"
    out_file.write_text(summary, encoding="utf-8")
    print(summary)
    print(f"\nDesign written to {out_file.resolve()}")


if __name__ == "__main__":
    main()
