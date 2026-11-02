"""One LightGBM regressor for every site, scored on the held-out months with the bake-off metrics."""

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor

from luckml.config import Config
from luckml.features import FEATURE_COLUMNS, TARGET

PARAMS = {
    "n_estimators": 200,
    "learning_rate": 0.05,
    "num_leaves": 15,
    "min_child_samples": 5,
    "random_state": 7,
    "verbose": -1,
}
RISK = 0.20


def fit(train: pd.DataFrame) -> LGBMRegressor:
    m = LGBMRegressor(**PARAMS)
    m.fit(train[FEATURE_COLUMNS], train[TARGET])
    return m


def wape(pred: np.ndarray, actual: np.ndarray) -> float:
    return float(np.abs(pred - actual).sum() / actual.sum())


def evaluate(m, holdout: pd.DataFrame, history: pd.DataFrame) -> dict:
    """Metrics on the held-out rows with a positive actual, as fractions. The gate reads wape; the rest is reported."""
    scored = holdout[holdout[TARGET] > 0].reset_index(drop=True)
    actual = scored[TARGET].to_numpy(dtype=float)
    pred = np.asarray(m.predict(scored[FEATURE_COLUMNS]), dtype=float)
    if len(actual) == 0:
        return {"rows": 0, "wape": float("nan")}
    signed = pred - actual
    ape = np.abs(signed) / actual
    persistence = scored[["LAG_1", "LAG_2", "LAG_3"]].to_numpy(dtype=float).mean(axis=1)
    last_year = scored[["SITE_ID", "MONTH"]].assign(MONTH=lambda d: pd.to_datetime(d["MONTH"]) - pd.DateOffset(months=12))
    seasonal = last_year.merge(history[["SITE_ID", "MONTH", TARGET]], on=["SITE_ID", "MONTH"], how="left")[TARGET]
    return {
        "rows": len(actual),
        "wape": wape(pred, actual),
        "mape": float(ape.mean()),
        "median_ape": float(np.median(ape)),
        "p90_ape": float(np.quantile(ape, 0.9)),
        "bias": float(signed.sum() / actual.sum()),
        "rmse": float(np.sqrt(np.mean(signed**2))),
        "stockout_rate": float(np.mean(signed < -RISK * actual)),
        "excess_rate": float(np.mean(signed > RISK * actual)),
        "persistence_wape": wape(persistence, actual),
        "seasonal_naive_wape": wape(seasonal.to_numpy(dtype=float), actual) if seasonal.notna().all() else None,
    }


def gate(metrics: dict, cfg: Config) -> bool:
    return metrics["wape"] <= cfg.gate_wape_max
