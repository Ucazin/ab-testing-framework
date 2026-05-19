"""
03_validity_checks.py — sample-ratio mismatch + segment balance checks.

Prints a pass/fail report. Run before trusting any analysis.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from stats import srm_check  # noqa: E402

DATA = Path("data")


def main() -> None:
    df = pd.read_parquet(DATA / "experiment.parquet")

    # 1. Overall SRM
    n_control   = int((df["arm"] == "control").sum())
    n_treatment = int((df["arm"] == "treatment").sum())
    ok, p = srm_check(n_control, n_treatment, planned_split=0.5)
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] Overall SRM check:  control={n_control:,}  treatment={n_treatment:,}  chi² p = {p:.3f}")

    # 2. SRM within each segment — catches bugs where one device-class
    #    is over-represented in one arm.
    print()
    print("Per-segment SRM:")
    for seg in ("device", "country"):
        for value, sub in df.groupby(seg):
            nc = int((sub["arm"] == "control").sum())
            nt = int((sub["arm"] == "treatment").sum())
            ok, p = srm_check(nc, nt, planned_split=0.5)
            status = "ok" if ok else "FAIL"
            print(f"  {seg}={value!s:<10} c={nc:>5}  t={nt:>5}  chi² p = {p:.3f}  [{status}]")

    # 3. Pre-period AA check — pre_revenue means should not differ between arms
    print()
    pre_mean_c = df.loc[df["arm"] == "control",   "pre_revenue"].mean()
    pre_mean_t = df.loc[df["arm"] == "treatment", "pre_revenue"].mean()
    delta = pre_mean_t - pre_mean_c
    print(f"Pre-experiment revenue AA check:")
    print(f"  control mean   = {pre_mean_c:.3f}")
    print(f"  treatment mean = {pre_mean_t:.3f}")
    print(f"  difference     = {delta:+.3f}")
    print()
    print("If any check is FAIL, do NOT trust the analysis — investigate assignment bugs first.")


if __name__ == "__main__":
    main()
