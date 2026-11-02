"""The environment steps around a model version, run from the bundle's sql/ scripts by the pipeline and the task graph."""

import json
from pathlib import Path

from luckml.config import Config

SQL_DIR = Path(__file__).resolve().parents[1] / "sql"


def statements(text: str, **values) -> list[str]:
    """Splits a script on top-level semicolons, keeping $$ scripting blocks whole, and fills <% name %> variables."""
    for k, v in values.items():
        text = text.replace(f"<% {k} %>", str(v))
    out, buf, in_block = [], [], False
    for line in text.splitlines():
        if not buf and (not line.strip() or line.lstrip().startswith("--")):
            continue
        buf.append(line)
        if line.count("$$") % 2:
            in_block = not in_block
        if not in_block and line.rstrip().endswith(";"):
            out.append("\n".join(buf).rstrip().rstrip(";").rstrip())
            buf = []
    if buf and "\n".join(buf).strip():
        out.append("\n".join(buf).strip())
    return out


def run(session, name: str, **values) -> list:
    rows = []
    for stmt in statements((SQL_DIR / f"{name}.sql").read_text(), **values):
        rows = session.sql(stmt).collect()
    return rows


def log_run(session, cfg: Config, run_id: str, stage: str, version: str, passed: bool, detail: dict) -> None:
    session.sql(
        f"insert into {cfg.database}.WORKSPACE.RUN_LOG (RUN_ID, STAGE, MODEL_VERSION, GATE_PASSED, METRICS, RUN_AT) "
        "select ?, ?, ?, ?, parse_json(?), current_timestamp()",
        params=[run_id, stage, version, passed, json.dumps(detail)],
    ).collect()


def gate(session, cfg: Config, version: str, run_id: str) -> None:
    run(session, "actuals", db=cfg.database)
    try:
        rows = run(session, "regression", db=cfg.database, version=version, tolerance=cfg.regression_tolerance)
    except Exception as e:
        log_run(session, cfg, run_id, "gate", version, False, {"error": str(e)[:500]})
        raise
    verdict = str(rows[0][0]) if rows else ""
    print(verdict)
    log_run(session, cfg, run_id, "gate", version, True, {"verdict": verdict})


def promote(session, cfg: Config, version: str, run_id: str) -> None:
    row = run(session, "verify", db=cfg.database, version=version)[0]
    checks = {k: row[k] for k in ("FORECAST_ROWS", "NULL_FORECASTS", "VERSION_PRESENT")}
    print(checks)
    if row["FORECAST_ROWS"] == 0 or row["NULL_FORECASTS"] > 0 or row["VERSION_PRESENT"] == 0:
        log_run(session, cfg, run_id, "promote", version, False, checks)
        raise RuntimeError(f"{version} failed verification")
    run(session, "monitor", db=cfg.database, version=version, wh=cfg.warehouse)
    run(session, "set_default", db=cfg.database, version=version)
    retired = run(session, "retire", db=cfg.database, keep=cfg.retain_versions) if cfg.retire_enabled else []
    if retired:
        print(retired)
    log_run(session, cfg, run_id, "promote", version, True, {**checks, "retired": str(retired[0][0]) if retired else "disabled"})
