import re
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "dcm" / "assets" / "luckml" / "sql"


def test_monitor_reads_only_its_versions_rows():
    sql = (SCRIPTS / "monitor.sql").read_text()
    assert re.search(r"CREATE OR REPLACE VIEW <% db %>\.WORKSPACE\.FORECAST_<% version %>", sql)
    assert re.search(r"WHERE MODEL_VERSION = '<% version %>'", sql)
    assert re.search(r"SOURCE = <% db %>\.WORKSPACE\.FORECAST_<% version %>\s", sql)
    assert "SOURCE = <% db %>.WORKSPACE.FORECAST_SITE_MONTH" not in sql


def test_actuals_refresh_fills_only_missing_actuals_from_the_source_view():
    sql = (SCRIPTS / "actuals.sql").read_text()
    assert "UPDATE <% db %>.WORKSPACE.FORECAST_SITE_MONTH" in sql
    assert "<% db %>.WORKSPACE.SRC_SITE_MONTH" in sql
    assert re.search(r"ACTUAL_TONNES IS NULL", sql)


def test_regression_gate_compares_the_candidate_with_the_default_and_raises():
    sql = (SCRIPTS / "regression.sql").read_text()
    assert '"is_default_version"' in sql
    assert "<% tolerance %>" in sql
    assert "RAISE" not in sql and "RETURN 'FAIL " in sql
    assert "no default to compare" in sql


def test_regression_gate_compares_weighted_errors():
    sql = (SCRIPTS / "regression.sql").read_text()
    assert sql.count("SUM(ABS(") == 2 and "AVG(ABS(" not in sql
    assert "wape" in sql


def test_monitor_has_a_baseline_view_of_the_versions_training_rows():
    sql = (SCRIPTS / "monitor.sql").read_text()
    assert re.search(r"CREATE OR REPLACE VIEW <% db %>\.WORKSPACE\.BASELINE_<% version %> AS\s+SELECT \* FROM <% db %>\.WORKSPACE\.BASELINE_SITE_MONTH WHERE MODEL_VERSION = '<% version %>'", sql)
    assert re.search(r"BASELINE = <% db %>\.WORKSPACE\.BASELINE_<% version %>\s", sql)


def test_verify_counts_the_versions_baseline_rows():
    sql = (SCRIPTS / "verify.sql").read_text()
    assert re.search(r"FROM <% db %>\.WORKSPACE\.BASELINE_SITE_MONTH WHERE MODEL_VERSION = '<% version %>'\) AS baseline_rows", sql)
