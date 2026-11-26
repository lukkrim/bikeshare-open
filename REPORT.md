# Forecasting daily Capital Bikeshare demand under a leakage contract

## Results

_Written in the report commit._

## Headline finding

_Written in the report commit._

## Exercise 4: target transformation

**Mechanism, checked first.** A tree cannot predict above the largest target it was trained on. The 2011
training maximum is 6,043 rides; 39% of validation days and 57% of test days exceed it. Untransformed hgb
never predicts above about 5,470. Its validation MAE is 1,994.5 rides on days above the training maximum
and 872.4 on days within range. Tuning does not fix this: `max_iter=300`, learning rate 0.05 and
`min_samples_leaf=10` only move validation R^2 from 0.2266 to 0.2553. So the weak validation score comes from
the level shift, not mainly from the 306 training rows or the default settings.

**Transformation.** Fit hgb on `cnt / cnt_roll_7` ("how busy is today relative to the previous week"), then
multiply the prediction by `cnt_roll_7` to get rides back. `cnt_roll_7` is the mean of the 7 days *before* d,
so it is known at prediction time. The ratio spans 0.16–1.88 in training and 0.16–1.69 in validation, so the
trees no longer need to extrapolate. The code is behind `python -m src.train --ratio-target`, which writes
`reports/metrics_ratio_target.json`; `reports/metrics.json` stays untransformed.

| hgb target (validation only while iterating) | Valid R^2 | Valid MAE | max prediction |
|---|---|---|---|
| raw `cnt` (as in metrics.json) | 0.2266 | 1310.1 | 5,466 |
| `log1p(cnt)` | 0.1418 | 1357.2 | 5,424 |
| `cnt - cnt_lag_1` | 0.6102 | 828.2 | 8,201 |
| `cnt / cnt_roll_28` | 0.6851 | 717.7 | 8,421 |
| **`cnt / cnt_roll_7`** | **0.7439** | **697.4** | 8,257 |

The log transform fails for the predicted reason: it is still bounded by the training maximum. On validation,
ratio-target hgb beats ridge by +0.060 R^2 (paired bootstrap 95% CI [+0.007, +0.114]). **Test, touched once
after the choice:** ratio hgb R^2 0.6117 / MAE 851.9, vs ridge 0.6239 / 879.3 and persistence 0.5099 / 840.1.
Gradient boosting goes from the worst model (−0.54) to roughly level with ridge, with a better MAE than ridge.
Ridge fitted on the same ratio target gets much worse (valid 0.438, test 0.089), so the transform suits trees, not
the linear model.

**Defensible, with one caveat.** It targets the mechanism we identified before trying it. The scaling variable is
known on day d. Predictions are converted back to rides, so they compare directly with the baselines, and the
baselines are unchanged. Nothing was chosen on test. The caveat: I picked it from four candidates on validation,
and the validation gain (+0.52 R^2) shrinks on test (+1.15 over raw hgb but still slightly below ridge), so part of
the validation margin is selection. It is a real fix for a real mechanism, not a way to win, but the best honest
summary is "competitive with ridge", not "better than ridge".

## Exercise 5: ridge vs. persistence

Ridge is not worth deploying over "predict yesterday's count" as it stands. It wins on R^2 (test 0.6239 vs
0.5099, +0.114, 95% CI [+0.003, +0.259]; validation +0.233) but loses on MAE (test 879.3 vs 840.1 rides) and
beats persistence on only 43% of test days. The metric that matters for running the system is MAE in rides: a
rebalancing crew or a staffing plan pays for every ride of error on every day, while R^2 is dominated by a few
very large misses. The two metrics disagree because ridge avoids big misses (10 test days off by more than 2,000
rides vs 17 for persistence; RMSE 1,068 vs 1,219) but is worse on a typical day (median absolute error 807 vs
506), and it under-predicts by 427 rides on average, while persistence is unbiased (−16). The standardised
coefficients show what ridge learned: recent demand (`cnt_roll_7` +403, `cnt_lag_1` +321, `cnt_roll_28` +165)
plus weather (`weather_severity` −290, `temp` +228, `windspeed` −160). Its intercept is anchored to the 2011 level,
which is the source of the bias. Two more points argue against deploying it. Its R^2 edge only just clears zero.
And it is an upper bound, because ridge is given the observed weather on the day while persistence gets nothing.
A real forecast would use less accurate weather forecasts. A fix worth testing on genuinely new data is to
subtract ridge's validation bias (+396). I computed that on test after the fact (MAE 716), so it is a hypothesis,
not evidence. Until then, persistence is the better default.

## Attribution

_Written in the report commit._
