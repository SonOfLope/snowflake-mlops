"""Reads the feature view into pandas."""

import pandas as pd

from luckml.config import Config

COLUMNS = ["SITE_ID", "MONTH", "TONNES", "LAG_1", "LAG_2", "LAG_3", "MONTH_NUM"]


def feature_view_name(cfg: Config) -> str:
    return f"{cfg.database}.FEATURES.{cfg.feature_view}${cfg.feature_view_version}"


def load_feature_frame(session, cfg: Config) -> pd.DataFrame:
    df = session.table(feature_view_name(cfg)).select(*COLUMNS).to_pandas()
    df["MONTH"] = pd.to_datetime(df["MONTH"])
    for c in ("TONNES", "LAG_1", "LAG_2", "LAG_3"):
        df[c] = df[c].astype(float)
    df["MONTH_NUM"] = df["MONTH_NUM"].astype(int)
    df["SITE_ID"] = df["SITE_ID"].astype(int)
    return df.sort_values(["SITE_ID", "MONTH"]).reset_index(drop=True)
