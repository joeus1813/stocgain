# Forecast findings — verified stored results

Read from the current run's persisted forecast evaluations on 2026-10-14. Eight rolling origins, 28-day forecast targets; observed in-stock evaluation excludes censored days. Overlapping origins mean observations are not independent experiments. Raw evidence: `perf/raw/stage4_forecast.json`.

| Basis | stocgain WAPE | 28-day naive WAPE | Difference |
|---|---:|---:|---:|
| Observed in-stock sales (993,797 observations) | 57.66% | 58.39% | 0.73 percentage points lower; approximately 1.25% relative |
| Simulation-only latent demand (1,075,200 observations) | 55.86% | 57.40% | 1.54 percentage points lower; approximately 2.68% relative |

This is a modest improvement, not high forecasting accuracy. WAPE is total absolute error divided by total actual units, not a percent-correct score. Observed MAE is 1.2142 units versus 1.2298 for naive. The model moves observed bias from naive's −6.00% to +5.12%, so removing downward bias does not eliminate error.

The aggregate hides uneven results. On smooth demand, WAPE improves from 46.61% to 45.29%; on erratic demand it **worsens** from 69.01% to 71.20%. Intermittent demand is effectively tied (106.26% versus 106.21%), and lumpy demand improves only slightly (87.61% to 87.43%). WAPE may exceed 100% and is unstable at low target volumes. These rows use origin-specific segment assignments; they are not static product classifications.

Likely explanations consistent with the design, not proven causal attributions: censoring-aware EWMA reduces the downward pressure of stockout zeros, but excluding censored/promoted days reduces the effective sample; recent-demand weighting can amplify noisy spikes. A 56-day history cannot establish annual seasonality, and planned promotion lift differs from realized synthetic lift. A simple trailing average is a strong baseline when demand is stable. The larger gain on hidden demand is consistent with censoring correction, but the model does not read that hidden truth.

No significance test, confidence interval or real-retailer validation was performed. The synthetic generator and forecasts are different mechanisms but are still designed within one project. Claim reproducible, leakage-tested decision support, not a proven reduction in real stockouts or increased profit. A future challenger should be evaluated on the same held-out origins and segment metrics before replacing the approved model; no model redesign was performed in this stage.
