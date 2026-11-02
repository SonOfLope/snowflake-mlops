from pathlib import Path

import pytest

from luckml import config, ops

SQL = Path(__file__).resolve().parents[1] / "dcm" / "assets" / "luckml" / "sql"


class FakeSession:
    def __init__(self, rows=None, fail_on=None):
        self.statements = []
        self.rows = rows or {}
        self.fail_on = fail_on

    def sql(self, text, params=None):
        self.statements.append(text)
        if self.fail_on and self.fail_on in text:
            raise RuntimeError("the candidate is worse than the default version beyond the tolerance")
        self._last = text
        return self

    def collect(self):
        for key, rows in self.rows.items():
            if key in self._last:
                return rows
        return []


def test_statements_keep_scripting_blocks_whole_and_fill_variables():
    text = "SHOW VERSIONS IN MODEL <% db %>.M;\nEXECUTE IMMEDIATE $$\nBEGIN\n  RETURN 1;\nEND;\n$$;\nSELECT '<% version %>';\n"
    out = ops.statements(text, db="DEV_ML_DB", version="V1")
    assert out == ["SHOW VERSIONS IN MODEL DEV_ML_DB.M", "EXECUTE IMMEDIATE $$\nBEGIN\n  RETURN 1;\nEND;\n$$", "SELECT 'V1'"]


def test_every_bundle_script_renders_without_leftover_variables():
    values = {"db": "DEV_ML_DB", "version": "V1", "tolerance": "0.1", "keep": "50", "wh": "ML_WH"}
    for path in SQL.glob("*.sql"):
        for stmt in ops.statements(path.read_text(), **values):
            assert "<%" not in stmt, path.name


def test_gate_refreshes_actuals_then_compares_with_the_configured_tolerance():
    s = FakeSession()
    ops.gate(s, config.load("dev"), "V9")
    assert "UPDATE DEV_ML_DB.WORKSPACE.FORECAST_SITE_MONTH" in s.statements[0]
    assert any("1 + 0.1" in t for t in s.statements)


def test_gate_failure_raises():
    with pytest.raises(RuntimeError):
        ops.gate(FakeSession(fail_on="RAISE"), config.load("dev"), "V9")


def test_promote_stops_when_verify_finds_no_rows():
    s = FakeSession(rows={"forecast_rows": [{"FORECAST_ROWS": 0, "NULL_FORECASTS": 0, "VERSION_PRESENT": 1}]})
    with pytest.raises(RuntimeError):
        ops.promote(s, config.load("dev"), "V9")
    assert not any("SET DEFAULT_VERSION" in t for t in s.statements)


def test_promote_monitors_then_sets_the_default_and_skips_retire_when_disabled():
    s = FakeSession(rows={"forecast_rows": [{"FORECAST_ROWS": 48, "NULL_FORECASTS": 0, "VERSION_PRESENT": 1}]})
    ops.promote(s, config.load("dev"), "V9")
    monitor = next(i for i, t in enumerate(s.statements) if "CREATE MODEL MONITOR" in t)
    default = next(i for i, t in enumerate(s.statements) if "SET DEFAULT_VERSION = V9" in t)
    assert monitor < default
    assert not any("DROP VERSION" in t for t in s.statements)


def test_forecast_without_a_version_uses_the_default(monkeypatch):
    from jobs import forecast as job
    from luckml import data, forecast, registry, session

    seen = {}
    monkeypatch.setattr(session, "connect", lambda cfg: FakeSession())
    monkeypatch.setattr(registry, "default_version", lambda s, cfg: "V7")
    monkeypatch.setattr(registry, "get_version", lambda s, cfg, v: seen.setdefault("v", v))
    monkeypatch.setattr(data, "load_feature_frame", lambda s, cfg: None)
    monkeypatch.setattr(job.features, "training_frame", lambda h: h)
    monkeypatch.setattr(job.features, "split_last_months", lambda f, n: (None, None))
    monkeypatch.setattr(forecast, "backfill_frame", lambda mv, h: None)
    monkeypatch.setattr(forecast, "predict_horizon", lambda mv, h, n: None)
    monkeypatch.setattr(job.pd, "concat", lambda frames: None)
    monkeypatch.setattr(forecast, "write", lambda s, cfg, rows, v, r: seen.setdefault("written", v) and 0)
    assert job.main(["--env", "dev", "--run-id", "m1"]) == 0
    assert seen == {"v": "V7", "written": "V7"}
