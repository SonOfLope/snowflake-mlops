import re
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "dcm" / "assets" / "luckml" / "sql"


def test_monitor_reads_only_its_versions_rows():
    sql = (SCRIPTS / "monitor.sql").read_text()
    assert re.search(r"CREATE OR REPLACE VIEW <% db %>\.<% schema %>\.<% model %>_<% version %> AS\s+SELECT \* FROM <% db %>\.<% schema %>\.SITE_MONTH_FORECAST WHERE MODEL = '<% model %>' AND MODEL_VERSION = '<% version %>'", sql)
    assert re.search(r"SOURCE = <% db %>\.<% schema %>\.<% model %>_<% version %>\s", sql)
    assert re.search(r"CREATE MODEL MONITOR IF NOT EXISTS <% db %>\.MODELS\.<% model %>_<% version %>_MON", sql)
    assert "SITE_MONTH_FORECAST\n" not in sql.split("SOURCE =")[1]


def test_actuals_refresh_fills_only_missing_actuals_from_the_source_view():
    sql = (SCRIPTS / "actuals.sql").read_text()
    assert "UPDATE <% db %>.<% schema %>.SITE_MONTH_FORECAST" in sql
    assert "<% db %>.WORKSPACE.SRC_SITE_MONTH" in sql
    assert re.search(r"ACTUAL_TONNES IS NULL", sql)


def test_regression_gate_compares_the_candidate_with_the_default_and_raises():
    sql = (SCRIPTS / "regression.sql").read_text()
    assert '"is_default_version"' in sql
    assert "<% tolerance %>" in sql
    assert "RAISE" not in sql and "RETURN 'FAIL " in sql
    assert "no default to compare" in sql
    assert "MODEL <% db %>.MODELS.<% model %>" in sql and "MODEL = '<% model %>'" in sql


def test_regression_gate_compares_weighted_errors():
    sql = (SCRIPTS / "regression.sql").read_text()
    assert sql.count("SUM(ABS(") == 2 and "AVG(ABS(" not in sql
    assert "wape" in sql


def test_monitor_snapshots_the_versions_training_rows_as_its_baseline_table():
    sql = (SCRIPTS / "monitor.sql").read_text()
    assert re.search(r"CREATE OR REPLACE TABLE <% db %>\.<% schema %>\.<% model %>_<% version %>_BASELINE AS\s+SELECT \* FROM <% db %>\.<% schema %>\.SITE_MONTH_BASELINE WHERE MODEL = '<% model %>' AND MODEL_VERSION = '<% version %>'", sql)
    assert re.search(r"BASELINE = <% db %>\.<% schema %>\.<% model %>_<% version %>_BASELINE\s", sql)
    assert "CREATE OR REPLACE VIEW <% db %>.<% schema %>.<% model %>_<% version %>_BASELINE" not in sql   # a monitor clones its baseline, a view cannot be cloned


def test_verify_counts_the_versions_baseline_rows():
    sql = (SCRIPTS / "verify.sql").read_text()
    assert re.search(r"FROM <% db %>\.<% schema %>\.SITE_MONTH_BASELINE WHERE MODEL = '<% model %>' AND MODEL_VERSION = '<% version %>'\) AS baseline_rows", sql)


def test_no_script_names_the_model_or_its_schema():
    for path in SCRIPTS.glob("*.sql"):
        text = path.read_text()
        assert "SITE_TONNES_FORECAST" not in text and "SALES_FORECASTING" not in text, path.name
