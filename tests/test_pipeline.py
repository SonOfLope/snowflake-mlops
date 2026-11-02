import re
from pathlib import Path

import yaml

PIPELINE = Path(__file__).resolve().parents[1] / "azure-pipelines.yml"
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


def test_every_environment_sets_the_default_after_the_gate_and_the_verify():
    text = (PIPELINE.parent / "pipelines" / "templates" / "deploy-env.yml").read_text()
    names = re.findall(r"displayName:\s*(.+)", text)
    gate = next(i for i, n in enumerate(names) if n.startswith("Actuals and regression gate"))
    verify = next(i for i, n in enumerate(names) if n.startswith("Verify and monitor"))
    default = next(i for i, n in enumerate(names) if n.startswith("Set the default version"))
    assert gate < verify < default
    block = text[text.index("Set the default version") - 400 : text.index("Set the default version")]
    assert "isProd" not in block


def test_the_regression_tolerance_comes_from_the_environment_configuration():
    text = (PIPELINE.parent / "pipelines" / "templates" / "deploy-env.yml").read_text()
    assert "regressionTolerance" not in text
    assert "regression_tolerance" in text


def test_jobs_run_as_the_code_bundle_declared_by_dcm():
    root = PIPELINE.parent
    manifest = yaml.safe_load((root / "dcm" / "manifest.yml").read_text())
    assert manifest["assets"]["luckml"]["path"] == "assets/luckml/**/*"
    assert (root / "dcm" / "assets" / "luckml" / "code_bundle.yml").is_file()
    definitions = (root / "dcm" / "sources" / "definitions" / "workspace.sql").read_text()
    assert re.search(r"DEFINE CODE BUNDLE \{\{ db \}\}\.WORKSPACE\.LUCKML\s+FROM 'asset://luckml/'", definitions)
    template = (root / "pipelines" / "templates" / "deploy-env.yml").read_text()
    assert "luckml.submit" not in template and "snow stage copy" not in template
    assert template.count("scripts/run_job.sql") == 2
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
    assert template.count("scripts/job_output.sql") == 2
    sql = (PIPELINE.parent / "scripts" / "job_output.sql").read_text()
    assert "CODE_BUNDLE_HISTORY" in sql and "RECORD_TYPE = 'LOG'" in sql
