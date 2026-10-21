"""Feature frames: what the model trains on, what it is scored on, and the months ahead it forecasts."""

import pandas as pd

FEATURE_COLUMNS = ["LAG_1", "LAG_2", "LAG_3", "MONTH_NUM"]
TARGET = "TONNES"
HORIZON_COLUMNS = ["SITE_ID", "MONTH", "MONTH_NUM", "LAG_1", "LAG_2", "LAG_3"]


def training_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Rows with every lag known; a site with fewer than four months contributes nothing."""
    return df.dropna(subset=FEATURE_COLUMNS).reset_index(drop=True)


def split_last_months(df: pd.DataFrame, n: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(train, holdout) where holdout is the last n distinct months in the frame."""
    cut = sorted(df["MONTH"].unique())[-n:]
    mask = df["MONTH"].isin(cut)
    return df[~mask].reset_index(drop=True), df[mask].reset_index(drop=True)


def horizon_frame(df: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """The next `horizon` months per site with lags from history where known.

    A site needs four months of history, one complete training row. Month 1 carries the three last actuals. Months 2 and 3 carry only the actuals still inside their
    window; the caller fills the rest from its own predictions, one month at a time.
    """
    rows = []
    for site_id, g in df.sort_values("MONTH").groupby("SITE_ID"):
        tonnes = g[TARGET].tolist()
        if len(tonnes) < 4:
            continue
        last = pd.Timestamp(g["MONTH"].iloc[-1])
        for h in range(1, horizon + 1):
            month = last + pd.DateOffset(months=h)
            lags = [tonnes[-(k - h + 1)] if k >= h else None for k in (1, 2, 3)]
            rows.append(
                {
                    "SITE_ID": site_id,
                    "MONTH": month,
                    "MONTH_NUM": month.month,
                    "LAG_1": lags[0],
                    "LAG_2": lags[1],
                    "LAG_3": lags[2],
                }
            )
    return pd.DataFrame(rows, columns=HORIZON_COLUMNS)
