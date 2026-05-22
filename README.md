# A/B Testing Framework

> 🌐 **Live walkthrough:** https://ucazin.github.io/ab-testing-framework/

A working framework for designing, analyzing, and **deciding on** A/B experiments — the kind every product analyst gets handed in their first week. Built around a realistic synthetic experiment ("we changed the checkout button color and want to know if conversion went up"), but the toolkit is dataset-agnostic.

Most A/B-test portfolio projects stop at "I ran a t-test." This one demonstrates the full lifecycle: **pre-experiment sizing, mid-experiment guardrails, post-experiment analysis with variance reduction, and a written ship/no-ship decision.**

## What's inside

### 1. Pre-experiment design (`src/01_design.py`)
- **Power analysis** — given a baseline conversion rate and the smallest effect we care about, how many users per arm?
- Sample size for two-proportion and two-sample t-tests
- Test duration estimator given traffic volume

### 2. Experiment data simulation (`src/02_simulate.py`)
- 60,000 users, two arms, binary outcome (purchased y/n) + continuous outcome (revenue per user)
- Configurable true effect; default = **+8% relative lift** in conversion
- Pre-experiment revenue as a CUPED covariate

### 3. Validity checks (`src/03_validity_checks.py`)
- **SRM test** (chi-square) — overall + per-segment, catches assignment bugs that invalidate the whole experiment
- **Pre-period AA test** — placebo check confirming the random assignment didn't show bogus differences

### 4. Analysis (`src/04_analyze.py`)
- Two-proportion z-test (conversion)
- Welch's t-test (revenue)
- Bootstrap CI (10k resamples) as a robust cross-check
- **CUPED variance reduction** using pre-experiment user revenue
- Multiple-testing correction (Benjamini-Hochberg) for segment breakouts
- Auto-generates `outputs/DECISION_DOC.md` — the ship/no-ship memo

## Business scenario

> **Hypothesis:** Changing the "Pay Now" button on the checkout page from grey to high-contrast green will increase conversion-to-purchase by at least +8% (relative), without harming average revenue per visitor.
>
> **Decision rule:** Ship if conversion lift is statistically significant at α = 0.05 AND practically significant at ≥ +5% relative AND revenue-per-visitor is not statistically worse.

This is the structure that better-run product analytics teams (Microsoft, Booking, Airbnb, Spotify) use. Framework follows their published playbooks (see references at the bottom).

## Headline results

Run the four scripts (or read [`outputs/DECISION_DOC.md`](outputs/DECISION_DOC.md)) — these are the actual numbers from the simulated experiment:

| Metric | Control | Treatment | Lift | 95% CI | p-value |
|---|---|---|---|---|---|
| Conversion rate | 5.49% | 6.01% | **+0.52 pp (+9.4% rel)** | [+0.14 pp, +0.89 pp] | **0.0068** |
| Revenue / visitor | $2.388 | $2.613 | +$0.225 | [+$0.054, +$0.395] | 0.0097 |
| Revenue (CUPED) | — | — | +$0.224 | [+$0.054, +$0.394] | 0.0099 |

- **SRM:** chi² p = 0.215 — passes; per-segment also clean.
- **AA pre-period:** pre_revenue means balanced (+0.055).
- **Segments:** 1 / 8 had a negative point estimate (country=AU), but **0 are significant after BH correction**.

**Decision: SHIP.** Annualized revenue uplift at 12k visitors/day: ~$984k.

Full design rationale and stopping rules in [`outputs/01_design_summary.txt`](outputs/01_design_summary.txt); full breakdown by segment in stdout of `04_analyze.py`; the formal memo in [`outputs/DECISION_DOC.md`](outputs/DECISION_DOC.md).

## Charts

| # | Chart | What it shows |
|---|---|---|
| 02 | [`02_results.png`](outputs/02_results.png) | Conversion and revenue lift with 95% CIs |
| 03 | [`03_cuped_comparison.png`](outputs/03_cuped_comparison.png) | CI-width comparison: Welch / Bootstrap / CUPED |

## How to run

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 1. Decide what we need to detect (writes outputs/01_design_summary.txt)
python src/01_design.py

# 2. Simulate the experiment (writes data/experiment.parquet)
python src/02_simulate.py

# 3. Check the experiment is sound (prints pass/fail report)
python src/03_validity_checks.py

# 4. Analyze and decide (writes charts + DECISION_DOC.md)
python src/04_analyze.py
```

Each script is idempotent and uses a fixed seed (42) — numbers reproduce exactly.

## Tech Stack

- **Python 3.10+** — pandas, numpy, scipy, statsmodels, matplotlib, seaborn
- **CUPED implementation from scratch** — no `lifelines`, `expan`, or other A/B libraries
- Deterministic seeds throughout — every number in the README regenerates exactly

## Project Structure

```
03-ab-testing-framework/
├── src/
│   ├── 01_design.py            # Power / sample-size calculator
│   ├── 02_simulate.py          # Generate experiment data
│   ├── 03_validity_checks.py   # SRM + AA tests
│   ├── 04_analyze.py           # Full analysis pipeline + DECISION_DOC.md
│   └── stats.py                # Reusable: z-test, t-test, bootstrap, CUPED, SRM
├── data/                       # Simulated experiment (gitignored, regen via script)
├── outputs/
│   ├── 01_design_summary.txt
│   ├── 02_results.png
│   ├── 03_cuped_comparison.png
│   └── DECISION_DOC.md         # The ship/no-ship memo
├── MEMO.md                     # Why this framework, what it solves
├── README.md
├── LICENSE                     # MIT
├── requirements.txt
└── .gitignore
```

## Skills demonstrated

- Statistical hypothesis testing (proportions, means, bootstrap)
- Power analysis — knowing you need 48k users per arm before you start, not after
- **Variance reduction with CUPED** — the technique used at scale by Microsoft, Netflix, Booking
- **SRM detection** — the validity check most candidates skip
- Multiple-testing correction (Benjamini-Hochberg) on segment breakouts
- Decision-making, not just analysis — every test ends with a written recommendation
- Reproducibility — deterministic simulation, scripted pipeline, no manual cells

## Reading the CUPED result

In this synthetic experiment, CUPED gave a **θ ≈ 0.014**, meaning the pre-experiment revenue covariate is only weakly correlated with the in-experiment revenue. As a result, the CUPED CI is essentially the same width as the un-adjusted Welch CI.

This is intentional and instructive: **CUPED helps when you have a strong covariate, not always.** In production, you would build a richer covariate (last-30-day session count + page-view depth + tenure) and expect to see a 30–50% CI reduction. Code is implemented; the lever is on the analyst.

## Further reading (industry references)

- Kohavi, Tang, Xu — *Trustworthy Online Controlled Experiments* (Microsoft — the field bible)
- Deng, Xu, Kohavi, Walker — *Improving the Sensitivity of Online Controlled Experiments by Utilizing Pre-Experiment Data* (the CUPED paper)
- Airbnb engineering blog — *Sample Ratio Mismatch* posts
