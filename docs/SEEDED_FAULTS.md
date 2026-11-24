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
