import pandas as pd
import pytest


def _site_rows(site_id, months, tonnes):
    rows = []
    for i, (m, t) in enumerate(zip(months, tonnes)):
        rows.append(
            {
                "SITE_ID": site_id,
                "MONTH": pd.Timestamp(m),
                "TONNES": float(t),
                "LAG_1": float(tonnes[i - 1]) if i >= 1 else None,
                "LAG_2": float(tonnes[i - 2]) if i >= 2 else None,
                "LAG_3": float(tonnes[i - 3]) if i >= 3 else None,
                "MONTH_NUM": pd.Timestamp(m).month,
            }
        )
    return rows


@pytest.fixture
def feature_frame():
    """Site 101 with eight months, site 202 with three months (too short for lags)."""
    months_a = [f"2026-0{m}-01" for m in range(1, 9)]
    tonnes_a = [100, 110, 120, 130, 140, 150, 160, 170]
    months_b = ["2026-06-01", "2026-07-01", "2026-08-01"]
    tonnes_b = [10, 20, 30]
    return pd.DataFrame(_site_rows(101, months_a, tonnes_a) + _site_rows(202, months_b, tonnes_b))
