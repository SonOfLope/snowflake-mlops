import re
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def test_monitor_reads_only_its_versions_rows():
    sql = (SCRIPTS / "monitor.sql").read_text()
    assert re.search(r"CREATE OR REPLACE VIEW <% db %>\.WORKSPACE\.FORECAST_<% version %>", sql)
    assert re.search(r"WHERE MODEL_VERSION = '<% version %>'", sql)
    assert re.search(r"SOURCE = <% db %>\.WORKSPACE\.FORECAST_<% version %>\s", sql)
    assert "SOURCE = <% db %>.WORKSPACE.FORECAST_SITE_MONTH" not in sql


def test_promote_carries_the_version_comment():
    sql = (SCRIPTS / "promote.sql").read_text()
    assert "SHOW VERSIONS IN MODEL <% src_db %>.MODELS.SITE_TONNES_FORECAST" in sql
    assert re.search(r"MODIFY VERSION ' \|\| v \|\| ' SET COMMENT", sql)


def test_actuals_refresh_fills_only_missing_actuals_from_the_source_view():
    sql = (SCRIPTS / "actuals.sql").read_text()
    assert "UPDATE <% db %>.WORKSPACE.FORECAST_SITE_MONTH" in sql
    assert "<% db %>.WORKSPACE.SRC_SITE_MONTH" in sql
    assert re.search(r"ACTUAL_TONNES IS NULL", sql)


def test_regression_gate_compares_the_candidate_with_the_default_and_raises():
    sql = (SCRIPTS / "regression.sql").read_text()
    assert '"is_default_version"' in sql
    assert "<% tolerance %>" in sql
    assert re.search(r"RAISE \w+;", sql)
    assert "no default to compare" in sql
