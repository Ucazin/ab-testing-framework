# Decision Document — Checkout Button Color Experiment

**Decision:** **SHIP**

## Result Summary

| Metric                    | Control | Treatment | Lift          | 95% CI                 | p-value |
|---------------------------|---------|-----------|---------------|------------------------|---------|
| Conversion rate           | 0.0549  | 0.0601    | +0.0052 (+9.37%) | [+0.0014, +0.0089] | 0.0068 |
| Revenue / visitor (ARPV)  | $2.388 | $2.613  | $+0.225     | [$+0.054, $+0.395]   | 0.0097 |
| Revenue / visitor (CUPED) |       —      |       —        | $+0.224     | [$+0.054, $+0.394]   | 0.0099 |

## Validity

- SRM: chi² test passed (see `03_validity_checks.py` output).
- Pre-experiment AA: pre_revenue means balanced between arms.
- Segment breakouts: 1/8 segments had a negative point estimate, but 0/8 are significant after Benjamini-Hochberg correction — no individual segment is a confirmed regression.

## Recommendation

Ship the green button to 100% of traffic. Annualized impact estimate at current traffic of 12k visitors/day: revenue uplift of ~$984,150 per year.

## What Could Go Wrong

- The +9% lift might attenuate as the novelty effect fades. Monitor week-over-week for 4 weeks post-launch.
- The treatment shifted some users from "browse" to "buy" — total session count may drop slightly because converted users leave sooner.
- Mobile users showed the largest lift; if mobile traffic share shifts, real-world impact will shift with it.
