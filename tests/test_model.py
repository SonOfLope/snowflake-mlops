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
    metrics = model.evaluate(m, df.iloc[100:], df.iloc[:100])
    assert metrics["rows"] == 20
    assert metrics["wape"] < 0.1
    assert list(m.feature_name_) == FEATURE_COLUMNS


def test_gate_uses_the_weighted_error_and_the_configured_ceiling():
    cfg = config.load("dev")
    assert cfg.gate_wape_max == 0.4
    assert model.gate({"wape": 0.39, "mape": 0.9}, cfg) is True
    assert model.gate({"wape": 0.41, "mape": 0.1}, cfg) is False


def test_evaluate_excludes_zero_actuals():
    df = _linear_frame(n=40)
    m = model.fit(df.iloc[:30])
    holdout = df.iloc[30:].copy()
    holdout.loc[holdout.index[:5], "TONNES"] = 0.0
    assert model.evaluate(m, holdout, df.iloc[:30])["rows"] == 5


class _Fixed:
    """A model that returns a fixed forecast per row."""

    def __init__(self, preds):
        self.preds = np.array(preds, dtype=float)

    def predict(self, x):
        return self.preds


def _holdout(actuals, months):
    return pd.DataFrame(
        {"SITE_ID": 1, "MONTH": pd.to_datetime(months), "TONNES": actuals, "LAG_1": 90.0, "LAG_2": 120.0, "LAG_3": 150.0,
         "MONTH_NUM": pd.to_datetime(months).month}
    )


def test_metrics_follow_the_bake_off_definitions():
    holdout = _holdout([1000.0, 10.0], ["2026-07-01", "2026-08-01"])
    history = pd.DataFrame({"SITE_ID": [1, 1], "MONTH": pd.to_datetime(["2025-07-01", "2025-08-01"]), "TONNES": [900.0, 20.0]})
    m = model.evaluate(_Fixed([1100.0, 20.0]), holdout, history)
    assert m["rows"] == 2
    assert abs(m["wape"] - 110 / 1010) < 1e-9          # weighted: the big site dominates
    assert abs(m["mape"] - 0.55) < 1e-9                # plain: the small site's 100 percent miss dominates
    assert abs(m["bias"] - 110 / 1010) < 1e-9          # positive, both over-forecast
    assert abs(m["median_ape"] - 0.55) < 1e-9
    assert abs(m["p90_ape"] - 0.91) < 1e-9
    assert abs(m["rmse"] - np.sqrt((100**2 + 10**2) / 2)) < 1e-9
    assert m["stockout_rate"] == 0.0 and m["excess_rate"] == 0.5
    assert abs(m["persistence_wape"] - (abs(120 - 1000) + abs(120 - 10)) / 1010) < 1e-9   # trailing three-month average, 120
    assert abs(m["seasonal_naive_wape"] - (abs(900 - 1000) + abs(20 - 10)) / 1010) < 1e-9  # same month last year


def test_seasonal_naive_is_absent_without_last_years_months():
    holdout = _holdout([100.0], ["2026-07-01"])
    history = pd.DataFrame({"SITE_ID": [1], "MONTH": pd.to_datetime(["2026-01-01"]), "TONNES": [80.0]})
    assert model.evaluate(_Fixed([90.0]), holdout, history)["seasonal_naive_wape"] is None
