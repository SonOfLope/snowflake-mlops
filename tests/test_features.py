import pandas as pd

from luckml import features


def test_training_frame_drops_short_site(feature_frame):
    out = features.training_frame(feature_frame)
    assert (out["SITE_ID"] == 202).sum() == 0
    assert (out["SITE_ID"] == 101).sum() == 5


def test_split_last_months(feature_frame):
    train, holdout = features.split_last_months(features.training_frame(feature_frame), 3)
    assert sorted(holdout["MONTH"].dt.strftime("%Y-%m").unique()) == ["2026-06", "2026-07", "2026-08"]
    assert holdout["MONTH"].min() > train["MONTH"].max()


def test_horizon_frame_three_months(feature_frame):
    out = features.horizon_frame(feature_frame, 3)
    a = out[out["SITE_ID"] == 101]
    assert list(a["MONTH"].dt.strftime("%Y-%m")) == ["2026-09", "2026-10", "2026-11"]
    assert (out["SITE_ID"] == 202).sum() == 0


def test_horizon_lags_from_history(feature_frame):
    out = features.horizon_frame(feature_frame, 3)
    first = out[out["SITE_ID"] == 101].iloc[0]
    assert first["LAG_1"] == 170.0
    assert first["LAG_2"] == 160.0
    assert first["LAG_3"] == 150.0
    assert first["MONTH_NUM"] == 9
    assert pd.isna(out[out["SITE_ID"] == 101].iloc[1]["LAG_1"])
