"""Scores a model on the months ahead or on the held-out months, and writes the rows."""

import numpy as np
import pandas as pd

from luckml.config import Config
from luckml.features import FEATURE_COLUMNS, HORIZON_COLUMNS, TARGET, horizon_frame

OUTPUT_COLUMNS = HORIZON_COLUMNS + ["FORECAST_TONNES", "ACTUAL_TONNES"]


def _predict(m, frame: pd.DataFrame) -> pd.Series:
    """m is a registry version (run) or a model fitted in the same job (predict)."""
    if hasattr(m, "run"):
        scored = m.run(frame[FEATURE_COLUMNS].reset_index(drop=True), function_name="predict")
        new = [c for c in scored.columns if c not in FEATURE_COLUMNS]
        return pd.Series(scored[new[-1]].to_numpy(dtype=float), index=frame.index)
    return pd.Series(np.asarray(m.predict(frame[FEATURE_COLUMNS]), dtype=float), index=frame.index)


def predict_horizon(mv, hist: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """Month by month per site, each prediction becoming the next month's LAG_1."""
    frame = horizon_frame(hist, horizon)
    frame["FORECAST_TONNES"] = np.nan
    frame["ACTUAL_TONNES"] = np.nan
    frame["_H"] = frame.groupby("SITE_ID").cumcount()
    for h in range(horizon):
        idx = frame.index[frame["_H"] == h]
        if len(idx) == 0:
            break
        if h > 0:
            prev = frame[frame["_H"] == h - 1].set_index("SITE_ID")
            sites = frame.loc[idx, "SITE_ID"].to_numpy()
            frame.loc[idx, "LAG_1"] = prev.loc[sites, "FORECAST_TONNES"].to_numpy()
            frame.loc[idx, "LAG_2"] = prev.loc[sites, "LAG_1"].to_numpy()
            frame.loc[idx, "LAG_3"] = prev.loc[sites, "LAG_2"].to_numpy()
        frame.loc[idx, "FORECAST_TONNES"] = _predict(mv, frame.loc[idx]).to_numpy()
    for c in ("LAG_1", "LAG_2", "LAG_3", "FORECAST_TONNES", "ACTUAL_TONNES"):
        frame[c] = frame[c].astype(float)
    return frame[OUTPUT_COLUMNS].reset_index(drop=True)


def scored_frame(m, rows: pd.DataFrame) -> pd.DataFrame:
    """Rows with a known actual, scored by m: the held-out months by the fit that never saw them, or the training rows by the
    refitted version as its monitor's baseline."""
    out = rows[HORIZON_COLUMNS].copy()
    out["FORECAST_TONNES"] = _predict(m, rows)
    out["ACTUAL_TONNES"] = rows[TARGET].astype(float)
    return out[OUTPUT_COLUMNS].reset_index(drop=True)


def write(session, cfg: Config, rows: pd.DataFrame, version: str, run_id: str, table: str = "SITE_MONTH_FORECAST") -> int:
    """Merges rows into <schema>.<table> on (ROW_ID, MODEL, MODEL_VERSION); a rerun rewrites, never duplicates."""
    staged = rows.copy()
    staged["ROW_ID"] = staged["SITE_ID"].astype(int).astype(str) + "-" + pd.to_datetime(staged["MONTH"]).dt.strftime("%Y-%m")
    staged["MODEL"] = cfg.model_name
    staged["MODEL_VERSION"] = version
    staged["RUN_ID"] = run_id
    staged["RUN_AT"] = pd.Timestamp.utcnow().tz_localize(None).strftime("%Y-%m-%d %H:%M:%S")
    staged["MONTH"] = pd.to_datetime(staged["MONTH"]).dt.strftime("%Y-%m-%d")
    temp = f"FORECAST_STAGE_{run_id}".upper().replace("-", "_")
    session.write_pandas(staged, temp, database=cfg.database, schema="WORKSPACE", auto_create_table=True,
                         table_type="temporary", overwrite=True, quote_identifiers=False)
    cols = ["ROW_ID", "SITE_ID", "MONTH", "MONTH_NUM", "LAG_1", "LAG_2", "LAG_3", "FORECAST_TONNES",
            "ACTUAL_TONNES", "MODEL", "MODEL_VERSION", "RUN_ID", "RUN_AT"]
    source = (
        "select ROW_ID, SITE_ID, to_timestamp_ntz(MONTH) as MONTH, MONTH_NUM, LAG_1, LAG_2, LAG_3, FORECAST_TONNES, "
        f"ACTUAL_TONNES, MODEL, MODEL_VERSION, RUN_ID, to_timestamp_ntz(RUN_AT) as RUN_AT from {cfg.database}.WORKSPACE.{temp}"
    )
    updates = ", ".join(f"t.{c} = s.{c}" for c in ("FORECAST_TONNES", "ACTUAL_TONNES", "LAG_1", "LAG_2", "LAG_3", "RUN_ID", "RUN_AT"))
    session.sql(
        f"merge into {cfg.database}.{cfg.schema}.{table} t using ({source}) s "
        "on t.ROW_ID = s.ROW_ID and t.MODEL = s.MODEL and t.MODEL_VERSION = s.MODEL_VERSION "
        f"when matched then update set {updates} "
        f"when not matched then insert ({', '.join(cols)}) values ({', '.join('s.' + c for c in cols)})"
    ).collect()
    return len(staged)
