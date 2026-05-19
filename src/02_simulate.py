"""
02_simulate.py — generate a realistic experiment dataset.

Output: data/experiment.parquet (one row per user).

Columns
-------
user_id          str
arm              str   {control, treatment}
device           str   {mobile, desktop, tablet}
country          str   {US, CA, UK, AU, OTHER}
pre_revenue      float user's revenue in the 30 days BEFORE the experiment
                       — used as the CUPED covariate
converted        int   0 or 1
revenue          float revenue this session (0 if not converted)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
N_USERS = 60_000
DATA = Path("data"); DATA.mkdir(exist_ok=True)

BASELINE_CVR    = 0.050
TRUE_REL_LIFT   = 0.08             # +8% relative lift (the truth we want to detect)
TREATMENT_CVR   = BASELINE_CVR * (1 + TRUE_REL_LIFT)
AOV_CONTROL     = 43.50            # average order value (control)
AOV_TREATMENT   = 44.20            # tiny AOV lift, mostly the conversion drives revenue


def main() -> None:
    rng = np.random.default_rng(SEED)

    arm     = rng.choice(["control", "treatment"], size=N_USERS, p=[0.5, 0.5])
    device  = rng.choice(["mobile", "desktop", "tablet"], size=N_USERS, p=[0.62, 0.32, 0.06])
    country = rng.choice(["US", "CA", "UK", "AU", "OTHER"],
                         size=N_USERS, p=[0.55, 0.10, 0.12, 0.08, 0.15])

    # Pre-experiment revenue: lognormal, correlated with later conversion.
    # This is the covariate that makes CUPED effective.
    pre_revenue = rng.lognormal(mean=2.4, sigma=0.9, size=N_USERS) - 3.0
    pre_revenue = np.clip(pre_revenue, 0, None)

    # Conversion probability: baseline + treatment effect + small lift from pre_revenue
    p = np.where(arm == "control", BASELINE_CVR, TREATMENT_CVR)
    # users with non-zero pre_revenue convert ~2x as often
    p = p * (1 + 0.6 * np.tanh(pre_revenue / 50))
    converted = (rng.random(N_USERS) < p).astype(int)

    # Revenue per session: 0 if not converted, else AOV with some noise
    base_aov = np.where(arm == "control", AOV_CONTROL, AOV_TREATMENT)
    revenue = converted * rng.normal(base_aov, 14.0, size=N_USERS).clip(min=1.0)

    df = pd.DataFrame({
        "user_id":     [f"U{1+i:07d}" for i in range(N_USERS)],
        "arm":         arm,
        "device":      device,
        "country":     country,
        "pre_revenue": pre_revenue.round(2),
        "converted":   converted,
        "revenue":     revenue.round(2),
    })

    df.to_parquet(DATA / "experiment.parquet", index=False)
    print(f"experiment.parquet  {len(df):,} rows  ({DATA.resolve()})")
    print(df.groupby("arm").agg(
        users=("user_id", "count"),
        cvr=("converted", "mean"),
        arpv=("revenue", "mean"),
    ).round(4))


if __name__ == "__main__":
    main()
