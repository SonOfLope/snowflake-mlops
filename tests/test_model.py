import numpy as np
import pandas as pd

from luckml import config, model
from luckml.features import FEATURE_COLUMNS


def _linear_frame(n=120, seed=1):
    rng = np.random.default_rng(seed)
    lag1 = rng.uniform(50, 500, n)
    df = pd.DataFrame(
        {
            "SITE_ID": 101,
            "MONTH": pd.date_range("2016-01-01", periods=n, freq="MS"),
            "LAG_1": lag1,
            "LAG_2": lag1 * 0.9,
            "LAG_3": lag1 * 0.8,
            "MONTH_NUM": pd.date_range("2016-01-01", periods=n, freq="MS").month,
        }
    )
    df["TONNES"] = 2.0 * df["LAG_1"]
    return df


def test_fit_predicts_close_on_linear_data():
    df = _linear_frame()
    m = model.fit(df.iloc[:100])
    metrics = model.evaluate(m, df.iloc[100:])
    assert set(metrics) >= {"mape", "rows"}
    assert metrics["rows"] == 20
    assert metrics["mape"] < 0.1
    assert list(m.feature_name_) == FEATURE_COLUMNS


def test_gate_threshold():
    cfg = config.load("dev")
    assert cfg.gate_mape_max == 0.35
    assert model.gate({"mape": 0.34, "rows": 24}, cfg) is True
    assert model.gate({"mape": 0.36, "rows": 24}, cfg) is False


def test_evaluate_excludes_zero_actuals():
    df = _linear_frame(n=40)
    m = model.fit(df.iloc[:30])
    holdout = df.iloc[30:].copy()
    holdout.loc[holdout.index[:5], "TONNES"] = 0.0
    assert model.evaluate(m, holdout)["rows"] == 5
