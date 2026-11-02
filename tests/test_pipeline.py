import itertools
import re
from pathlib import Path

import yaml

PIPELINE = Path(__file__).resolve().parents[1] / "azure-pipelines.yml"
BUNDLE = PIPELINE.parent / "dcm" / "assets" / "luckml"
STAGE_REF = re.compile(r"stageDependencies\.(\w+)\.")


def _stages():
    return yaml.safe_load(PIPELINE.read_text())["stages"]


def _depends_on(stage):
    d = stage.get("dependsOn", [])
    return [d] if isinstance(d, str) else list(d)


def test_stage_outputs_are_read_only_from_direct_dependencies():
    for stage in _stages():
        text = yaml.safe_dump(stage)
        for referenced in set(STAGE_REF.findall(text)):
            assert referenced in _depends_on(stage), (
                f"stage {stage['stage']} reads outputs of {referenced} without depending on it directly"
            )


def test_step_display_names_carry_no_runtime_variable():
    template = PIPELINE.parent / "pipelines" / "templates" / "deploy-env.yml"
    names = re.findall(r"displayName:\s*(.+)", template.read_text())
    assert names
    for name in names:
        assert "$(" not in name and "modelVersion" not in name, name


def test_every_environment_trains_its_own_challenger_then_forecasts_gates_and_promotes():
    text = (PIPELINE.parent / "pipelines" / "templates" / "deploy-env.yml").read_text()
    names = [n.split(" (")[0] for n in re.findall(r"displayName:\s*(.+)", text)]
    assert names[-4:] == ["Train", "Forecast", "Regression gate", "Promote"]
    assert text.count("${{ if") == 1 and "previousDb" not in text and "modelVersion" not in text
    assert "promote.sql" not in text


def test_no_stage_reads_another_stages_model():
    stages = {s["stage"]: s for s in _stages()}
    assert "stageDependencies" not in yaml.safe_dump(stages["Test"]) + yaml.safe_dump(stages["Prod"])
    assert _depends_on(stages["Prod"]) == ["Test"]


def test_jobs_run_as_the_code_bundle_declared_by_dcm():
    root = PIPELINE.parent
    manifest = yaml.safe_load((root / "dcm" / "manifest.yml").read_text())
    assert manifest["assets"]["luckml"]["path"] == "assets/luckml/**/*"
    assert (root / "dcm" / "assets" / "luckml" / "code_bundle.yml").is_file()
    definitions = (root / "dcm" / "sources" / "definitions" / "workspace.sql").read_text()
    assert re.search(r"DEFINE CODE BUNDLE \{\{ db \}\}\.WORKSPACE\.LUCKML\s+FROM 'asset://luckml/'", definitions)
    template = (root / "pipelines" / "templates" / "deploy-env.yml").read_text()
    assert "luckml.submit" not in template and "snow stage copy" not in template
    assert template.count("scripts/run_job.sql") == 4
    sql = (root / "scripts" / "run_job.sql").read_text()
    assert "EXECUTE CODE BUNDLE <% db %>.WORKSPACE.LUCKML" in sql
    assert "CODE_BUNDLE_HISTORY" in sql


def test_the_bundle_pins_its_runtime_and_writes_results_to_job_results():
    spec = yaml.safe_load((PIPELINE.parent / "dcm" / "assets" / "luckml" / "code_bundle.yml").read_text())["bundle"]
    assert spec["compute_options"]["runtime_version"] == "2.10.0"
    assert spec["compute_options"]["language_version"] == "3.12"
    assert spec["properties"]["result_stage"] == "@WORKSPACE.JOB_RESULTS"
    definitions = (PIPELINE.parent / "dcm" / "sources" / "definitions" / "workspace.sql").read_text()
    assert "DEFINE STAGE {{ db }}.WORKSPACE.JOB_RESULTS" in definitions


def test_job_steps_print_the_jobs_own_output_even_when_the_job_fails():
    template = (PIPELINE.parent / "pipelines" / "templates" / "deploy-env.yml").read_text()
    assert template.count("scripts/job_output.sql") == 4
    sql = (PIPELINE.parent / "scripts" / "job_output.sql").read_text()
    assert "CODE_BUNDLE_HISTORY" in sql and "RECORD_TYPE = 'LOG'" in sql and "TELEMETRY.EVENTS_VIEW" in sql


def test_retirement_is_configured_per_environment_and_starts_disabled():
    for env in ("dev", "test", "prod"):
        cfg = yaml.safe_load((BUNDLE / "config" / f"{env}.yml").read_text())
        assert cfg["retire_enabled"] is False
        assert cfg["retain_versions"] == 50
    sql = (BUNDLE / "sql" / "retire.sql").read_text()
    assert "DROP MODEL MONITOR IF EXISTS" in sql and "DROP VIEW IF EXISTS" in sql
    assert sql.index("DROP MODEL MONITOR") < sql.index("DROP VIEW") < sql.index("DROP VERSION")
    assert "DROP TABLE IF EXISTS <% db %>.<% schema %>.<% model %>_' || r.v || '_BASELINE" in sql and sql.index("_BASELINE") < sql.index("DROP VERSION")
    assert "DROP VIEW IF EXISTS <% db %>.WORKSPACE.FORECAST_' || r.v" in sql and "DROP TABLE IF EXISTS <% db %>.WORKSPACE.BASELINE_' || r.v" in sql   # the names before SALES_FORECASTING
    assert "is_default_version" in sql and "<% keep %>" in sql


def _columns(definitions, schema, table):
    block = definitions[definitions.index(f"DEFINE TABLE {{{{ db }}}}.{schema}.{table} ("):]
    block = block[: block.index("\n)")]
    return [line.strip().split()[0] for line in block.splitlines()[1:] if line.strip()]


def test_the_baseline_table_mirrors_the_forecast_table_so_the_monitor_can_compare_them():
    definitions = (PIPELINE.parent / "dcm" / "sources" / "definitions" / "sales_forecasting.sql").read_text()
    forecast = _columns(definitions, "SALES_FORECASTING", "SITE_MONTH_FORECAST")
    assert _columns(definitions, "SALES_FORECASTING", "SITE_MONTH_BASELINE") == forecast
    assert forecast[-1] == "MODEL"    # appended last, so the tables moved from WORKSPACE can be altered into shape


def test_the_move_runs_once_before_the_deploy_and_keeps_the_old_names_for_earlier_monitors():
    template = (PIPELINE.parent / "pipelines" / "templates" / "deploy-env.yml").read_text()
    assert template.index("scripts/move_tables.sql") < template.index("snow dcm deploy")
    sql = (PIPELINE.parent / "scripts" / "move_tables.sql").read_text()
    assert "SYSTEM$UNMANAGE_FROM_DCM_PROJECT" in sql and "DROP DATA METRIC FUNCTION" in sql
    for old, new in (("FORECAST_SITE_MONTH", "SITE_MONTH_FORECAST"), ("BASELINE_SITE_MONTH", "SITE_MONTH_BASELINE")):
        assert f"RENAME TO <% db %>.SALES_FORECASTING.{new}" in sql
        assert f"CREATE VIEW <% db %>.WORKSPACE.{old}" in sql


def test_every_environment_names_the_family_schema():
    for env in ("dev", "test", "prod"):
        cfg = yaml.safe_load((BUNDLE / "config" / f"{env}.yml").read_text())
        assert cfg["schema"] == "SALES_FORECASTING" and cfg["model_name"] == "SITE_TONNES_FORECAST"


def test_the_monthly_cycle_is_a_task_graph_started_only_in_prod():
    manifest = yaml.safe_load((PIPELINE.parent / "dcm" / "manifest.yml").read_text())["templating"]
    assert manifest["defaults"]["cycle_state"] == "SUSPENDED"
    assert manifest["configurations"]["prod"]["cycle_state"] == "STARTED"
    assert "cycle_state" not in manifest["configurations"]["dev"] and "cycle_state" not in manifest["configurations"]["test"]
    sql = (PIPELINE.parent / "dcm" / "sources" / "definitions" / "cycle.sql").read_text()
    assert "DEFINE TASK GRAPH {{ db }}.SALES_FORECASTING.SITE_TONNES_MONTHLY\n" in sql and "{{ cycle_state }}" in sql
    order = ["SITE_TONNES_MONTHLY_TRAIN", "SITE_TONNES_MONTHLY_FORECAST_CHALLENGER", "SITE_TONNES_MONTHLY_GATE", "SITE_TONNES_MONTHLY_PROMOTE"]
    for before, after in itertools.pairwise(order):
        assert f"DEFINE TASK {{{{ db }}}}.SALES_FORECASTING.{after}\n  AFTER {{{{ db }}}}.SALES_FORECASTING.{before}" in sql
    assert "SITE_TONNES_MONTHLY_FORECAST_DEFAULT\n  AFTER {{ db }}.SALES_FORECASTING.SITE_TONNES_MONTHLY_START" in sql
    assert "WORKSPACE.LUCKML" in sql and "WORKSPACE.MLOPS" in sql and ".WORKSPACE.MONTHLY" not in sql
    assert sql.count("CURRENT_TASK_GRAPH_ORIGINAL_SCHEDULED_TIMESTAMP") == 5


def test_run_log_keeps_every_metric():
    definitions = (PIPELINE.parent / "dcm" / "sources" / "definitions" / "workspace.sql").read_text()
    run_log = definitions[definitions.index("DEFINE TABLE {{ db }}.WORKSPACE.RUN_LOG"):]
    run_log = run_log[: run_log.index(";")]
    assert "WAPE NUMBER(9,4)" in run_log and "METRICS VARIANT" in run_log
    assert run_log.index("METRICS VARIANT") < run_log.index("MODEL VARCHAR")


def test_prod_retrains_only_when_asked_dev_and_test_always():
    text = PIPELINE.read_text()
    params = yaml.safe_load(text)["parameters"]
    retrain = next(p for p in params if p["name"] == "retrainProd")
    assert retrain["type"] == "boolean" and retrain["default"] is False
    stages = {s["stage"]: yaml.safe_dump(s) for s in _stages()}
    assert "retrain: ${{ parameters.retrainProd }}" in stages["Prod"]
    assert "retrain:" not in stages["Dev"] and "retrain:" not in stages["Test"]
    template = (PIPELINE.parent / "pipelines" / "templates" / "deploy-env.yml").read_text()
    assert "${{ if eq(parameters.retrain, true) }}" in template
    assert template.index("${{ if eq(parameters.retrain, true) }}") < template.index("displayName: Train")


def test_data_expectations_are_declared_scheduled_and_checked_before_training():
    root = PIPELINE.parent / "dcm"
    quality = (root / "sources" / "definitions" / "quality.sql").read_text()
    for name in ("PREVIOUS_MONTH_PRESENT", "ENOUGH_HISTORY", "NO_NULL_TONNES", "NO_NEGATIVE_TONNES",
                 "ONE_ROW_PER_SITE_MONTH", "NO_NULL_FORECAST", "ONE_ROW_PER_VERSION_SITE_MONTH"):
        assert f"EXPECTATION {name} (" in quality
    workspace = (root / "sources" / "definitions" / "workspace.sql").read_text()
    family = (root / "sources" / "definitions" / "sales_forecasting.sql").read_text()
    assert workspace.count("DATA_METRIC_SCHEDULE = '{{ dq_schedule }}'") == 1 and family.count("DATA_METRIC_SCHEDULE = '{{ dq_schedule }}'") == 1
    assert "TO TABLE {{ db }}.SALES_FORECASTING.SITE_MONTH_FORECAST" in quality and "ON (ROW_ID, MODEL, MODEL_VERSION)" in quality
    defaults = yaml.safe_load((root / "manifest.yml").read_text())["templating"]["defaults"]
    assert {"dq_schedule", "max_source_age_seconds", "min_source_rows"} <= set(defaults)
    template = (PIPELINE.parent / "pipelines" / "templates" / "deploy-env.yml").read_text()
    assert template.index("snow dcm deploy") < template.index("snow dcm test") < template.index("displayName: Train")
    cycle = (root / "sources" / "definitions" / "cycle.sql").read_text()
    assert "SITE_TONNES_MONTHLY_CHECK_DATA" in cycle and "TEST ALL" in cycle
    assert "DEFINE TASK {{ db }}.SALES_FORECASTING.SITE_TONNES_MONTHLY_TRAIN\n  AFTER {{ db }}.SALES_FORECASTING.SITE_TONNES_MONTHLY_CHECK_DATA" in cycle
