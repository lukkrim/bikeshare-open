"""The tests that make the agent honest.

test_no_forbidden_features is the single most valuable test in this repo:
casual + registered == cnt exactly, so any model handed those columns
scores R^2 = 1.0 and looks brilliant while having learned nothing.
"""
import pandas as pd
import pytest

from src.config import FORBIDDEN, TARGET
from src.features import build_features, feature_columns
from src.ingest import load_raw


@pytest.fixture(scope="module")
def feats():
    return build_features(load_raw())


def test_leakage_identity_holds(feats):
    """Documents *why* casual and registered are forbidden."""
    assert (feats.casual + feats.registered == feats[TARGET]).all()


def test_no_forbidden_features(feats):
    """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
    construction, so this cannot discover a *new* leaky column. What it
    catches is someone editing feature_columns() or FORBIDDEN -- which is
    exactly the fault the Step 7 hook demonstrates."""
    cols = set(feature_columns(feats))
    assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"


@pytest.fixture(scope="module")
def raw_cnt():
    """Ground truth by calendar date, from the raw file (not the feature
    table, which has already dropped the rows around the gap)."""
    return load_raw().set_index("dteday")[TARGET]


def _calendar_window(date, days):
    return [date - pd.Timedelta(days=k) for k in days]


def test_lags_are_true_calendar_lags(feats, raw_cnt):
    """cnt_lag_1 on d must equal raw cnt on d-1, cnt_lag_7 on d-7, on every
    row. A row whose source day is absent from the raw data must not exist
    at all: skipping it would hide a row-based shift across 2011-03-10."""
    for date, row in feats.set_index("dteday").iterrows():
        for col, k in (("cnt_lag_1", 1), ("cnt_lag_7", 7)):
            (src,) = _calendar_window(date, [k])
            assert src in raw_cnt.index, f"{col} on {date.date()} built from absent day {src.date()}"
            assert row[col] == pytest.approx(raw_cnt[src]), f"bad {col} at {date.date()}"


def test_lag_is_not_the_target(feats):
    assert not (feats.cnt_lag_1 == feats[TARGET]).all()


def test_rolling_mean_excludes_today(feats, raw_cnt):
    """cnt_roll_7 on d must be the mean of raw cnt on d-1..d-7 (calendar
    days, today excluded), on every row, with no window spanning a gap."""
    for date, value in feats.set_index("dteday").cnt_roll_7.items():
        window = _calendar_window(date, range(1, 8))
        absent = [d.date() for d in window if d not in raw_cnt.index]
        assert not absent, f"cnt_roll_7 on {date.date()} spans absent days {absent}"
        assert value == pytest.approx(raw_cnt[window].mean()), f"bad cnt_roll_7 at {date.date()}"


def test_no_missing_values(feats):
    assert feats[feature_columns(feats)].isna().sum().sum() == 0


def test_dates_are_sorted_and_unique(feats):
    assert feats.dteday.is_monotonic_increasing
    assert feats.dteday.is_unique
