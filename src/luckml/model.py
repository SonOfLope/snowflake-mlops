"""One LightGBM regressor for every site, scored by MAPE on the held-out months."""

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


def fit(train: pd.DataFrame) -> LGBMRegressor:
    m = LGBMRegressor(**PARAMS)
    m.fit(train[FEATURE_COLUMNS], train[TARGET])
    return m


def evaluate(m: LGBMRegressor, holdout: pd.DataFrame) -> dict:
    actual = holdout[TARGET].to_numpy(dtype=float)
    pred = m.predict(holdout[FEATURE_COLUMNS])
    mask = actual != 0
    mape = float(np.mean(np.abs(pred[mask] - actual[mask]) / actual[mask])) if mask.any() else float("nan")
    return {"mape": mape, "rows": int(mask.sum())}


def gate(metrics: dict, cfg: Config) -> bool:
    return metrics["mape"] <= cfg.gate_mape_max
