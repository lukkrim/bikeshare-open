"""Stage 3: split by date, fit two baselines and two models, write metrics.

  baseline_mean         the 2011 mean of cnt, every day
  baseline_persistence  yesterday's count (cnt_lag_1), nothing fitted
  ridge                 StandardScaler -> Ridge(alpha=1.0)
  hgb                   HistGradientBoostingRegressor, library defaults

Every model is fitted on train (2011) only. Valid (H1 2012) and test
(H2 2012) are scored, never fitted or tuned on.

Run: python -m src.train
"""
import json

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.config import METRICS, PROCESSED, TARGET, TRAIN_END, VALID_END
from src.features import feature_columns


class PersistenceBaseline(BaseEstimator, RegressorMixin):
    """Predict that today equals yesterday: returns `column` unchanged.

    Deliberately not a DummyRegressor: the comparison that matters for a
    lag-driven model is "does it beat yesterday's count", not "does it
    beat a constant"."""

    def __init__(self, column: str = "cnt_lag_1"):
        self.column = column

    def fit(self, X: pd.DataFrame, y=None):
        if self.column not in X.columns:
            raise ValueError(f"persistence baseline needs column {self.column!r}")
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return X[self.column].to_numpy(dtype=float)


MODELS = {
    "baseline_mean": DummyRegressor(strategy="mean"),
    "baseline_persistence": PersistenceBaseline("cnt_lag_1"),
    "ridge": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
    "hgb": HistGradientBoostingRegressor(random_state=0),
}


def temporal_split(df: pd.DataFrame):
    """Train = 2011, valid = H1 2012, test = H2 2012, by date. Never random:
    a random split puts a test day's neighbours (and its lagged count) in
    train."""
    dates = pd.to_datetime(df.dteday)
    train = df[dates <= TRAIN_END]
    valid = df[(dates > TRAIN_END) & (dates <= VALID_END)]
    test = df[dates > VALID_END]
    return train, valid, test


def score(model, part: pd.DataFrame, cols: list[str]) -> dict:
    pred = model.predict(part[cols])
    return {
        "r2": round(float(r2_score(part[TARGET], pred)), 4),
        "mae": round(float(mean_absolute_error(part[TARGET], pred)), 1),
    }


def fit_and_score(df: pd.DataFrame) -> dict:
    cols = feature_columns(df)
    train, valid, test = temporal_split(df)
    metrics = {}
    for name, model in MODELS.items():
        model.fit(train[cols], train[TARGET])
        metrics[name] = {"valid": score(model, valid, cols), "test": score(model, test, cols)}
    return metrics


if __name__ == "__main__":
    df = pd.read_parquet(PROCESSED)
    metrics = fit_and_score(df)
    METRICS.parent.mkdir(parents=True, exist_ok=True)
    METRICS.write_text(json.dumps(metrics, indent=2) + "\n")
    train, valid, test = temporal_split(df)
    # Valid only: test numbers stay in metrics.json, out of the iteration loop.
    summary = ", ".join(f"{k} valid r2={v['valid']['r2']}" for k, v in metrics.items())
    print(f"OK train: {len(train)}/{len(valid)}/{len(test)} rows, "
          f"{len(feature_columns(df))} features -> {METRICS.name}; {summary}")
