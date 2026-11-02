from pathlib import Path

import pytest

from luckml import config, ops

SQL = Path(__file__).resolve().parents[1] / "dcm" / "assets" / "luckml" / "sql"


class FakeSession:
    def __init__(self, rows=None):
        self.statements = []
        self.params = []
        self.rows = rows or {}

    def sql(self, text, params=None):
        self.statements.append(text)
        self.params.append(params)
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
    ops.gate(s, config.load("dev"), "V9", "run9")
    assert "UPDATE DEV_ML_DB.WORKSPACE.FORECAST_SITE_MONTH" in s.statements[0]
    assert any("1 + 0.1" in t for t in s.statements)


def test_gate_failure_raises_with_the_numbers():
    s = FakeSession(rows={"EXECUTE IMMEDIATE": [("FAIL V9 wape 0.25 against the default V8 wape 0.19, beyond the tolerance",)]})
    with pytest.raises(RuntimeError, match="V9 wape 0.25"):
        ops.gate(s, config.load("dev"), "V9", "run9")


def test_promote_stops_when_verify_finds_no_rows():
    s = FakeSession(rows={"forecast_rows": [{"FORECAST_ROWS": 0, "NULL_FORECASTS": 0, "VERSION_PRESENT": 1, "BASELINE_ROWS": 144}]})
    with pytest.raises(RuntimeError):
        ops.promote(s, config.load("dev"), "V9", "run9")
    assert not any("SET DEFAULT_VERSION" in t for t in s.statements)


def test_promote_stops_when_the_version_has_no_baseline_rows():
    s = FakeSession(rows={"forecast_rows": [{"FORECAST_ROWS": 48, "NULL_FORECASTS": 0, "VERSION_PRESENT": 1, "BASELINE_ROWS": 0}]})
    with pytest.raises(RuntimeError):
        ops.promote(s, config.load("dev"), "V9", "run9")
    assert not any("CREATE MODEL MONITOR" in t for t in s.statements)


def test_promote_monitors_then_sets_the_default_and_skips_retire_when_disabled():
    s = FakeSession(rows={"forecast_rows": [{"FORECAST_ROWS": 48, "NULL_FORECASTS": 0, "VERSION_PRESENT": 1, "BASELINE_ROWS": 144}]})
    ops.promote(s, config.load("dev"), "V9", "run9")
    monitor = next(i for i, t in enumerate(s.statements) if "CREATE MODEL MONITOR" in t)
    default = next(i for i, t in enumerate(s.statements) if "SET DEFAULT_VERSION = V9" in t)
    assert monitor < default
    assert not any("DROP VERSION" in t for t in s.statements)


class FakeVersion:
    def run(self, frame, function_name="predict"):
        return frame.assign(output_feature_0=frame["LAG_1"] * 1.0)


def test_forecast_without_a_version_uses_the_default(monkeypatch, feature_frame):
    from jobs import forecast as job
    from luckml import data, forecast, registry, session

    seen = {}
    monkeypatch.setattr(session, "connect", lambda cfg: FakeSession())
    monkeypatch.setattr(registry, "default_version", lambda s, cfg: "V7")
    monkeypatch.setattr(registry, "get_version", lambda s, cfg, v: seen.setdefault("v", v) and FakeVersion())
    monkeypatch.setattr(data, "load_feature_frame", lambda s, cfg: feature_frame)
    monkeypatch.setattr(forecast, "write", lambda s, cfg, rows, v, r: seen.setdefault("written", v) and 0)
    assert job.main(["--env", "dev", "--run-id", "m1"]) == 0
    assert seen == {"v": "V7", "written": "V7"}


def test_forecast_job_writes_only_the_months_ahead(monkeypatch, feature_frame):
    from jobs import forecast as job
    from luckml import data, forecast, registry, session

    written = []
    monkeypatch.setattr(session, "connect", lambda cfg: FakeSession())
    monkeypatch.setattr(registry, "get_version", lambda s, cfg, v: FakeVersion())
    monkeypatch.setattr(data, "load_feature_frame", lambda s, cfg: feature_frame)
    monkeypatch.setattr(forecast, "write", lambda s, cfg, rows, v, r: written.append(rows) or len(rows))
    assert job.main(["--env", "dev", "--version", "V9", "--run-id", "m1"]) == 0
    rows = written[0]
    assert len(rows) == 3 and rows["ACTUAL_TONNES"].isna().all()
    assert rows["MONTH"].min() > feature_frame["MONTH"].max()


def test_forecast_with_no_model_yet_writes_nothing(monkeypatch, capsys):
    import json

    from jobs import forecast as job
    from luckml import forecast, registry, session

    written = []
    monkeypatch.setattr(session, "connect", lambda cfg: FakeSession())
    monkeypatch.setattr(registry, "default_version", lambda s, cfg: None)
    monkeypatch.setattr(forecast, "write", lambda *a, **k: written.append(a))
    assert job.main(["--env", "prod", "--run-id", "m1"]) == 0
    assert written == []
    last = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert last["version"] is None and last["rows"] == 0


def test_gate_writes_its_run_log_row_even_when_it_fails():
    s = FakeSession(rows={"EXECUTE IMMEDIATE": [("FAIL V9 wape 0.25 against the default V8 wape 0.19, beyond the tolerance",)]})
    with pytest.raises(RuntimeError):
        ops.gate(s, config.load("dev"), "V9", "run9")
    logged = [p for t, p in zip(s.statements, s.params) if "insert into DEV_ML_DB.WORKSPACE.RUN_LOG" in t]
    assert len(logged) == 1 and logged[0][:4] == ["run9", "gate", "V9", False]


def test_promote_writes_its_run_log_row():
    s = FakeSession(rows={"forecast_rows": [{"FORECAST_ROWS": 48, "NULL_FORECASTS": 0, "VERSION_PRESENT": 1, "BASELINE_ROWS": 144}]})
    ops.promote(s, config.load("dev"), "V9", "run9")
    logged = [p for t, p in zip(s.statements, s.params) if "insert into DEV_ML_DB.WORKSPACE.RUN_LOG" in t]
    assert len(logged) == 1 and logged[0][:4] == ["run9", "promote", "V9", True]
