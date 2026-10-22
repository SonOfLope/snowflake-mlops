import re
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def test_monitor_reads_only_its_versions_rows():
    sql = (SCRIPTS / "monitor.sql").read_text()
    assert re.search(r"CREATE OR REPLACE VIEW <% db %>\.WORKSPACE\.FORECAST_<% version %>", sql)
    assert re.search(r"WHERE MODEL_VERSION = '<% version %>'", sql)
    assert re.search(r"SOURCE = <% db %>\.WORKSPACE\.FORECAST_<% version %>\s", sql)
    assert "SOURCE = <% db %>.WORKSPACE.FORECAST_SITE_MONTH" not in sql
