# Forecasting daily Capital Bikeshare demand under a leakage contract

## Results

Train = 2011, validation = H1 2012, test = H2 2012, split by date (`src.train.temporal_split`). Every model is fit
on train only. "Before" is the pipeline at `61e03fd` (14 features, 348 training rows); "after" adds `cnt_roll_28`
(15 features, 306 training rows, because `LAG_WARMUP` rises to 28) and matches `reports/metrics.json` exactly. The
182 validation and 184 test rows are the same in both. Reproduce with `make all && make test`
(`git checkout 61e03fd && make all` for the "before" rows).

| Model | Feature | Valid R^2 | Valid MAE | Test R^2 | Test MAE |
|---|---|---|---|---|---|
| baseline_mean | before | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| baseline_mean | after | -0.6894 | 1877.3 | -1.7717 | 2659.6 |
| baseline_persistence | before | 0.4507 | 900.6 | 0.5099 | 840.1 |
| baseline_persistence | after | 0.4507 | 900.6 | 0.5099 | 840.1 |
| ridge | before | 0.6475 | 832.9 | 0.5833 | 947.1 |
| ridge | after | 0.6839 | 777.5 | 0.6239 | 879.3 |
| hgb | before | 0.1659 | 1341.1 | -0.6179 | 2057.3 |
| hgb | after | 0.2266 | 1310.1 | -0.5400 | 2008.2 |

`baseline_mean` changes only because its training mean is now taken over 306 rows. Persistence uses no training
data, so it cannot change. hgb uses scikit-learn defaults (`max_iter=100`); the lesson's reference used 300, which
is why our hgb rows differ from it.

## Headline finding

A ridge model on calendar, same-day weather and lagged demand explains 62% of the variance in H2 2012 daily rides
(test R^2 0.6239), against 51% for simply predicting yesterday's count (0.5099). But it is **worse than that
baseline in rides**: test MAE 879.3 vs 840.1, and it wins on only 43% of days. The R^2 gap (+0.114, 95% CI
[+0.003, +0.259]) only just clears zero, and it assumes perfect weather forecasts. Predicting the 2011 mean is far
worse, with negative R^2 on both splits (test -1.7717), because ridership grew about 65% into 2012. The same shift
breaks gradient boosting: trained on 2011, whose maximum is 6,043 rides, it cannot predict the 57% of test days
above that, so its test R^2 is negative (-0.5400). It is worse than a constant on R^2, though still better than the
mean baseline. Losing to persistence and having a negative R^2 are different failures, and this pipeline has both.
Leakage would have hidden all of it: `casual + registered` reproduces `cnt` to a residual of 5.5e-12, giving
R^2 = 1.000. **Our feature, `cnt_roll_28`, raised validation R^2 by +0.036 for ridge and +0.061 for hgb (on the
same rows: +0.038 / +0.055), above the 0.01 bar, so we kept it.**

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

**Model: Claude Opus 5.5 (hosted, `claude-opus-5-5`, Anthropic API via Claude Code), not the default local
`qwen3.5:9b` (`bikeshare-coder`, Ollama, 64k context).** I switched before Step 1, because the course allows
hosted Opus for students with a Claude subscription. The override is in the gitignored
`.claude/settings.local.json`; the graded `.claude/settings.json` model line is unchanged. The Part 4 batch auditor
and the Exercise 3 `leakage-auditor` subagent also ran on Opus 5.5. Results here are not comparable with
small-model runs: for example, Opus did not fall for the Step 3 naive prompt, because CLAUDE.md's rule stopped it,
so the leaky R^2 = 1.000 came from `src.leakage_demo`. Exercise 6 was not done.

**Generated by the agent** (reviewed and run by me; see `git log`):
- `src/train.py` (rewritten from spec in Step 6; `RatioToLevel` and `--ratio-target` in Exercise 4)
- `cnt_roll_28` and the `WEEK`/`MONTH`/`LAG_WARMUP` split in `src/features.py` and `src/config.py`; `RAW_FEATURE_COLS`,
  `ENCODED_COLS`, `RAW_SHA256`; `verify_raw` in `src/ingest.py`
- Tests: `test_every_raw_column_is_classified`, `test_raw_features_reach_the_model`, `test_raw_data_is_pristine`,
  `test_roll_28_*`, the rewritten calendar lag and rolling tests, and the validation-split `test_beats_the_mean_baseline`
- `.claude/hooks/stop_require_green.sh`, the fixes to `check_leakage.sh` and `settings.json`, and `.claude/skills/seed-fault/SKILL.md`
- Makefile `$(PYTHON)`; `docs/SEEDED_FAULTS.md`, `docs/AUDIT.md`; the drafts of `docs/DECISIONS.md` lines and of this report

**My decisions** (each traces to `docs/DECISIONS.md`):
- What to predict: `cnt`, daily, from information available on day d (starter rules, lines 6-8, kept).
- What counts as leakage: `casual`/`registered` excluded as leakage; `cnt_2d_bfr` and time indexes excluded for
  different reasons (lines 6-8, 13); keep same-day weather but disclose it as an oracle (line 14).
- How to split: by date, 2011 / H1 2012 / H2 2012 (line 9; the test-touch record in line 29).
- Which baselines: mean and persistence next to every score (line 10; updated numbers in line 31).
- Gate design: keep the denylist, plus a strict classification test (line 15).
- My feature: `cnt_roll_28`, chosen from three screened candidates and kept (line 26).
- Raw-data guard: a hash pin over a PreToolUse pattern hook (line 27); hosted Opus for the auditor (line 28).
- Whether the answer is believable: the Exercise 4 "defensible" and Exercise 5 "not worth deploying" judgements
  (lines 33-34). Drafted by the agent with the evidence; I reviewed and adopted them.
- CLAUDE.md trim (line 11).
