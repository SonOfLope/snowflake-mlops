from luckml import config, forecast


class FakeVersion:
    def run(self, frame, function_name="predict"):
        return frame.assign(output_feature_0=frame["LAG_1"] * 1.0)


class FakeSession:
    def __init__(self):
        self.frames = []
        self.sqls = []

    def write_pandas(self, df, table_name, **kwargs):
        self.frames.append((table_name, df.copy()))

    def sql(self, text, params=None):
        self.sqls.append(text)

        class R:
            def collect(self_inner):
                return [[len(text)]]

        return R()


def test_predict_horizon_rolls_lags(feature_frame):
    out = forecast.predict_horizon(FakeVersion(), feature_frame, 3)
    a = out[out["SITE_ID"] == 101].reset_index(drop=True)
    assert len(a) == 3
    assert a.loc[0, "FORECAST_TONNES"] == 170.0
    assert a.loc[1, "LAG_1"] == a.loc[0, "FORECAST_TONNES"]
    assert a.loc[1, "LAG_2"] == 170.0
    assert a.loc[2, "LAG_1"] == a.loc[1, "FORECAST_TONNES"]
    assert a.loc[2, "LAG_3"] == 170.0
    assert (out["SITE_ID"] == 202).sum() == 0


def test_backfill_frame_scores_holdout(feature_frame):
    holdout = feature_frame[(feature_frame["SITE_ID"] == 101)].tail(3)
    out = forecast.backfill_frame(FakeVersion(), holdout)
    assert list(out["ACTUAL_TONNES"]) == [150.0, 160.0, 170.0]
    assert list(out["FORECAST_TONNES"]) == list(holdout["LAG_1"])


def test_write_is_idempotent(feature_frame):
    cfg = config.load("dev")
    rows = forecast.predict_horizon(FakeVersion(), feature_frame, 3)
    s = FakeSession()
    n1 = forecast.write(s, cfg, rows, "V9", "run9")
    n2 = forecast.write(s, cfg, rows, "V9", "run9")
    assert n1 == n2 == 3
    merges = [q for q in s.sqls if q.lstrip().upper().startswith("MERGE")]
    assert len(merges) == 2
    assert "T.ROW_ID = S.ROW_ID AND T.MODEL_VERSION = S.MODEL_VERSION" in merges[0].upper()
    staged = s.frames[0][1]
    assert staged.loc[staged["MONTH"] == "2026-09-01", "ROW_ID"].iloc[0] == "101-2026-09"
    assert set(staged["MODEL_VERSION"]) == {"V9"}
