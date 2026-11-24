"""Guard rails on the ingest contract and the trained model's behaviour."""
import pandas as pd
import pytest
from sklearn.metrics import r2_score

from src.config import (
    DATE_COL,
    ENCODED_COLS,
    FORBIDDEN,
    LAG_WARMUP,
    RAW,
    RAW_FEATURE_COLS,
    TARGET,
)
from src.features import build_features, feature_columns, reindex_to_calendar
from src.ingest import load_raw, verify_raw
from src.train import MODELS, temporal_split


@pytest.fixture(scope="module")
def raw():
    return load_raw().sort_values("dteday").reset_index(drop=True)


@pytest.fixture(scope="module")
def feats(raw):
    return build_features(raw)


def test_calendar_is_complete_before_lagging(raw):
    """The reindexed frame must have no gaps, or the lags are wrong."""
    grid = reindex_to_calendar(raw)
    assert set(grid.dteday.diff().dropna().dt.days.unique()) == {1}


def test_only_expected_rows_are_dropped(raw, feats):
    """Rows may only vanish for the lag warm-up or downstream of a genuinely
    absent day -- never because an encoder produced a silent NaN.

    Accounting: the first LAG_WARMUP days have no complete history. Each
    absent calendar day m costs the LAG_WARMUP rows after it (the longest
    window, cnt_roll_28, is NaN on m+1..m+28 and covers every shorter
    lag's NaNs). Day m itself was never in `raw`, so it is not a loss.
    The bound is exact for the current feature set; add a longer lag and
    LAG_WARMUP in src/config.py must grow with it.
    """
    full = pd.date_range(raw.dteday.min(), raw.dteday.max(), freq="D")
    missing_days = len(full) - len(raw)
    allowed_loss = LAG_WARMUP + LAG_WARMUP * missing_days
    lost = len(raw) - len(feats)
    assert lost <= allowed_loss, f"lost {lost} rows; expected at most {allowed_loss}"


def test_raw_data_is_pristine():
    """data/raw/ is read-only by contract. Permission rules stop the agent's
    Write/Edit tools, but not every Bash write; this catches what they miss,
    and the Stop hook runs it before any turn can end."""
    verify_raw(RAW)
    extra = sorted(p.name for p in RAW.parent.iterdir()
                   if p.name != RAW.name and not p.name.startswith("."))
    assert not extra, f"unexpected files in {RAW.parent.name}/: {extra}"


def test_every_raw_column_is_classified():
    """feature_columns() is a denylist, so a new numeric column in the raw
    CSV would silently become a feature. Read the header straight from disk
    (not via load_raw) and require each column in exactly one bucket."""
    header = pd.read_csv(RAW, nrows=0).columns
    buckets = {
        "FORBIDDEN": FORBIDDEN,
        "RAW_FEATURE_COLS": RAW_FEATURE_COLS,
        "ENCODED_COLS": ENCODED_COLS,
        "DATE_COL": {DATE_COL},
    }
    unclassified = [c for c in header if not any(c in b for b in buckets.values())]
    assert not unclassified, f"unclassified raw columns: {unclassified}"
    doubled = [c for c in header if sum(c in b for b in buckets.values()) > 1]
    assert not doubled, f"columns in more than one bucket: {doubled}"


def test_raw_features_reach_the_model(feats):
    """RAW_FEATURE_COLS must be what the model actually sees, or the
    classification above is a label, not a fact."""
    missing = RAW_FEATURE_COLS - set(feature_columns(feats))
    assert not missing, f"declared raw features not in feature set: {missing}"


def test_beats_the_mean_baseline(feats):
    """A model that cannot beat predicting the training mean is not a result."""
    cols = feature_columns(feats)
    train, _, test = temporal_split(feats)
    ridge = MODELS["ridge"]
    ridge.fit(train[cols], train[TARGET])
    assert r2_score(test[TARGET], ridge.predict(test[cols])) > 0.4


def test_persistence_baseline_is_reported():
    """The baseline that matters for a lag-driven model is 'yesterday again'.
    It must be in the comparison, whatever its score."""
    assert "baseline_persistence" in MODELS
