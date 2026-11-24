# Seeded faults

Each fault was seeded in the working tree (data faults in a temp copy), the real output captured, then reverted. Hook stderr is the PostToolUse `check_leakage.sh` message Claude Code returned to the agent after the edit (the `=` rulers are shortened to 80 columns; the text is otherwise as received). "Agent turns to fix" counts tool calls the agent spent restoring green after seeing the failure.

## 1. Forbidden column added to `feature_columns`

- **Fault** (`src/features.py`):
  ```diff
  -    return [c for c in numeric if c not in FORBIDDEN]
  +    return [c for c in numeric if c not in FORBIDDEN] + ["casual"]
  ```
- **Predicted:** `test_no_forbidden_features`, since `casual` is in `FORBIDDEN`. Not `test_beats_the_mean_baseline`: a leaky ridge scores higher, not lower.
- **Caught by:** `tests/test_leakage.py::test_no_forbidden_features` (by the PostToolUse hook immediately, and by `make test`). Prediction matched.
- **Hook stderr:**
  ```
  Leakage tests failed after editing /Users/wanfranek/Documents/DSC 180AB Capstone/MA6/bikeshare-open/src/features.py:
  .F.......                                                                [100%]
  =================================== FAILURES ===================================
  E   AssertionError: forbidden columns in feature set: {'casual'}
      assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_28', 'cnt_roll_7', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})
  /Users/wanfranek/Documents/DSC 180AB Capstone/MA6/bikeshare-open/tests/test_leakage.py:31: AssertionError: forbidden columns in feature set: {'casual'}
  =========================== short test summary info ============================
  FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: forbidden columns in feature set: {'casual'}
  1 failed, 8 passed in 0.68s
  ```
- **`make test` output** (complete):
  ```
  python -m pytest tests/ -q
  .......F..........                                                       [100%]
  =================================== FAILURES ===================================
  __________________________ test_no_forbidden_features __________________________
  
  feats =         dteday  instant  season  ...  cnt_lag_7   cnt_roll_7  cnt_roll_28
  0   2011-01-31     31.0  WINTER  ...     141....142857  4071.321429
  671 2012-12-31    731.0  WINTER  ...      920.0  1531.428571  3969.428571
  
  [672 rows x 29 columns]
  
      def test_no_forbidden_features(feats):
          """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
          construction, so this cannot discover a *new* leaky column. What it
          catches is someone editing feature_columns() or FORBIDDEN -- which is
          exactly the fault the Step 7 hook demonstrates."""
          cols = set(feature_columns(feats))
  >       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
  E       AssertionError: forbidden columns in feature set: {'casual'}
  E       assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_28', 'cnt_roll_7', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})
  
  tests/test_leakage.py:31: AssertionError
  =========================== short test summary info ============================
  FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
  1 failed, 17 passed in 1.70s
  make: *** [test] Error 1
  ```
- **Fix:** `git checkout -- src/features.py`; suite back to `18 passed`.
- **Agent turns to fix:** 1.

## 2. `.shift(1)` deleted from `cnt_roll_7`

- **Fault** (`src/features.py`):
  ```diff
  -    out["cnt_roll_7"] = out[TARGET].shift(1).rolling(WEEK).mean()
  +    out["cnt_roll_7"] = out[TARGET].rolling(WEEK).mean()
  ```
- **Predicted:** `test_rolling_mean_excludes_today`, at the first feature row, because the window now includes today's `cnt`. Nothing else: row count and column names are unchanged.
- **Caught by:** `tests/test_leakage.py::test_rolling_mean_excludes_today` ("bad cnt_roll_7 at 2011-01-31": 1112.0 includes 2011-01-31 itself, expected 1099.86 from 01-24..01-30). Prediction matched.
- **Why it matters:** the leak looks like a gain. With it, validation R^2 is ridge 0.7541 / hgb 0.2900 vs the honest 0.6839 / 0.2266. Without the test, this would read as "+0.07, keep it".
- **Hook stderr:**
  ```
  Leakage tests failed after editing /Users/wanfranek/Documents/DSC 180AB Capstone/MA6/bikeshare-open/src/features.py:
  ....F....                                                                [100%]
  =================================== FAILURES ===================================
  E   AssertionError: bad cnt_roll_7 at 2011-01-31
      assert 1112.0 == 1099.857142857143 ± 0.00109986
        
        comparison failed
        Obtained: 1112.0
        Expected: 1099.857142857143 ± 0.00109986
  /Users/wanfranek/Documents/DSC 180AB Capstone/MA6/bikeshare-open/tests/test_leakage.py:67: AssertionError: bad cnt_roll_7 at 2011-01-31
  =========================== short test summary info ============================
  FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - AssertionError: bad cnt_roll_7 at 2011-01-31
  1 failed, 8 passed in 0.76s
  ```
- **`make test` output** (complete):
  ```
  python -m pytest tests/ -q
  ..........F.......                                                       [100%]
  =================================== FAILURES ===================================
  _______________________ test_rolling_mean_excludes_today _______________________
  
  feats =         dteday  instant  season  ...  cnt_lag_7   cnt_roll_7  cnt_roll_28
  0   2011-01-31     31.0  WINTER  ...     141....428571  4071.321429
  671 2012-12-31    731.0  WINTER  ...      920.0  1789.857143  3969.428571
  
  [672 rows x 29 columns]
  raw_cnt = dteday
  2011-01-03    1349
  2011-01-04    1562
  2011-01-05    1600
  2011-01-06    1606
  2011-01-07    1510
                .....  2114
  2012-12-28    3095
  2012-12-29    1341
  2012-12-30    1796
  2012-12-31    2729
  Name: cnt, Length: 728, dtype: int64
  
      def test_rolling_mean_excludes_today(feats, raw_cnt):
          """cnt_roll_7 on d must be the mean of raw cnt on d-1..d-7 (calendar
          days, today excluded), on every row, with no window spanning a gap."""
          for date, value in feats.set_index("dteday").cnt_roll_7.items():
              window = _calendar_window(date, range(1, 8))
              absent = [d.date() for d in window if d not in raw_cnt.index]
              assert not absent, f"cnt_roll_7 on {date.date()} spans absent days {absent}"
  >           assert value == pytest.approx(raw_cnt[window].mean()), f"bad cnt_roll_7 at {date.date()}"
  E           AssertionError: bad cnt_roll_7 at 2011-01-31
  E           assert 1112.0 == 1099.857142857143 ± 0.00109986
  E             
  E             comparison failed
  E             Obtained: 1112.0
  E             Expected: 1099.857142857143 ± 0.00109986
  
  tests/test_leakage.py:67: AssertionError
  =========================== short test summary info ============================
  FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - AssertionErr...
  1 failed, 17 passed in 1.67s
  make: *** [test] Error 1
  ```
- **Fix:** `git checkout -- src/features.py`, rebuilt features and metrics; suite back to `18 passed`.
- **Agent turns to fix:** 1.
