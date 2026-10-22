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
