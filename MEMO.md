# Memo — Why this A/B framework exists

**To:** Hiring manager
**From:** Lucca Cesar, Data Analyst
**Re:** What this project demonstrates that a "t-test on Iris" doesn't

## The gap most junior portfolios have

90% of A/B-testing projects in junior portfolios are one of two things:
1. A scipy `ttest_ind` on a tutorial dataset, with the conclusion "p < 0.05, ship it."
2. A bayesian post-hoc explainer with no decision rule and no validity checks.

Neither is what running an experiment at a real company looks like. A real experiment has **four phases**, and at any single phase a junior analyst can sink the whole experiment:

| Phase | What can sink it | What I built here |
|---|---|---|
| Design | Underpowered → false negatives | `01_design.py` — explicit sample size + duration calc |
| Run | Sample ratio mismatch (SRM) | `03_validity_checks.py` — chi² per segment, fail-loud |
| Analysis | Variance not reduced → CIs too wide | `stats.cuped_welch_t` — CUPED from scratch |
| Decision | "p < 0.05" without a rule | `04_analyze.py` writes [DECISION_DOC.md](outputs/DECISION_DOC.md) — explicit ship rule |

## What the demo experiment showed

On the simulated checkout-button experiment (60k users, +8% true relative lift):

- **Conversion +9.4% relative** (p = 0.0068, 95% CI [+0.14 pp, +0.89 pp]).
- **Revenue / visitor +$0.22** (p = 0.0097), confirmed by bootstrap and CUPED.
- SRM clean overall and across all 8 device/country segments.
- 1 segment (country=AU) showed a negative point estimate but did not survive BH correction.
- **Decision: ship**, annualized impact ~$984k at the current traffic of 12k/day.

## What this is honest about

- **CUPED's θ was 0.014** in this run — pre_revenue is a weak covariate of in-experiment revenue, so CUPED's CI shrinkage was negligible (~0.1%). I documented this in the README as a learning rather than hide it. CUPED helps when you have a strong covariate; selecting that covariate is itself a skill.
- **Synthetic data.** The +8% lift is a parameter I set in `02_simulate.py`. The point of the project is the *machinery*, not the discovery — every lever (effect size, baseline CVR, traffic, AOV) is configurable.

## Why a hiring manager should care

When this analyst is handed an A/B test on day one, they will:
- Compute power *before* the test starts, not after.
- Check SRM and AA on day 2, not on day 14.
- Apply CUPED when the covariate is strong, document why when it isn't.
- Write the decision doc with a stopping rule, not a paragraph of waffle.
- Run BH-corrected segment breakouts before claiming "no harmful segment."

That is the difference between a junior analyst who can run a test and one who can be trusted with the test.
