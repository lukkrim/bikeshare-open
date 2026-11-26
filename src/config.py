"""Single source of truth for paths, columns, and split dates."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "bike_daily.csv"
# The raw file is read-only by contract. `make data` and
# tests/test_contract.py check this hash, so a write that slips past the
# agent's permission rules (Bash cp, a script) still turns the build red.
RAW_SHA256 = "a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc"
PROCESSED = ROOT / "data" / "processed" / "features.parquet"
METRICS = ROOT / "reports" / "metrics.json"
METRICS_RATIO = ROOT / "reports" / "metrics_ratio_target.json"  # Exercise 4 only

# Daily Capital Bikeshare counts (Fanaee-T & Gama). Canonical home:
#   https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset
# We use the processed copy from Molnar's "Interpretable Machine Learning"
# because the UCI host blocks some campus networks. It differs from UCI:
#   - 728 rows, 2011-01-03 to 2012-12-31 (UCI has 731 from 2011-01-01)
#   - 2011-03-10 is absent (the UCI row records humidity 0, a sensor
#     artefact, and the mirror's cleaning dropped the whole day)
#   - `weather` is the labels GOOD / MISTY / BAD, not UCI's codes 1-4
#   - two extra columns: `days_since_2011` and `cnt_2d_bfr`
DATA_URL = (
    "https://raw.githubusercontent.com/christophM/"
    "interpretable-ml-book/master/data/bike.csv"
)

TARGET = "cnt"

# --- Three reasons a column is kept out of the feature set --------------

# 1. Leakage: the target or an arithmetic restatement of it.
#    casual + registered == cnt exactly, on every row. A model handed these
#    scores R^2 ~ 1.0 and has learned addition. At prediction time you would
#    not know either input: they are components of the thing being predicted.
LEAKAGE_COLS = {"casual", "registered", "cnt"}

# 2. Time indexes: not leakage, but a bad bet. A tree splits on "after date
#    X" and predicts a flat constant for every future date; a linear model
#    extrapolates a two-year trend we have no reason to trust. Excluding
#    them keeps the model comparison about what each does with lagged demand.
TIME_INDEX_COLS = {"instant", "yr", "days_since_2011"}

# 3. Unverified: `cnt_2d_bfr` is a two-day lag of cnt that shipped with the
#    mirror. It is NOT leakage -- a two-day-old count is known at prediction
#    time -- but we did not build it and cannot test how it was aligned, so we
#    build our own lags from the target and test those instead.
UNVERIFIED_COLS = {"cnt_2d_bfr"}

# What feature_columns() and the tests actually enforce.
FORBIDDEN = LEAKAGE_COLS | TIME_INDEX_COLS | UNVERIFIED_COLS

# --- Every other raw column, classified --------------------------------
# feature_columns() is a denylist: any numeric column not in FORBIDDEN is
# admitted. So that a new raw column cannot slip in (or out) unnoticed,
# tests/test_contract.py requires every raw column to sit in exactly one
# of FORBIDDEN, RAW_FEATURE_COLS, ENCODED_COLS, or be DATE_COL.

DATE_COL = "dteday"

# Same-day weather, passed to the model as-is. Observed on the target day,
# so scores assume a perfect next-day forecast (see docs/DECISIONS.md).
RAW_FEATURE_COLS = {"temp", "atemp", "hum", "windspeed"}

# Text labels never passed raw. holiday, workday, weather are encoded in
# src.features.build_features; season, mnth, weekday are redundant with the
# month_sin/month_cos/dayofweek features derived from dteday.
ENCODED_COLS = {"season", "mnth", "holiday", "weekday", "workday", "weather"}

# Temporal split: train on 2011, validate on H1 2012, test on H2 2012.
TRAIN_END = "2011-12-31"
VALID_END = "2012-06-30"

# Lag / rolling windows in src/features.py, in calendar days.
WEEK = 7      # cnt_lag_7, cnt_roll_7
MONTH = 28    # cnt_roll_28

# Longest window above. The first LAG_WARMUP calendar days have no complete
# history and are dropped; tests/test_contract.py uses this to bound how many
# rows may legitimately disappear. Never use it as a lag length itself.
LAG_WARMUP = max(WEEK, MONTH)
