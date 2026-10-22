"""Runs a job entry point as a Snowflake ML Job on the compute pool and waits for it."""

import argparse
import json
import sys

from snowflake.ml.jobs import submit_from_stage

from luckml import config, session
from luckml.config import Config

WAIT_SECONDS = 1800


def run(cfg: Config, job: str, version: str, run_id: str, build_dir: str) -> dict:
    s = session.connect(cfg)
    stage = f"{cfg.database}.WORKSPACE.CODE"
    ml_job = submit_from_stage(
        f"@{stage}/{build_dir}/",
        cfg.compute_pool,
        entrypoint=f"jobs/{job}.py",
        stage_name=stage,
        args=["--env", cfg.env, "--version", version, "--run-id", run_id],
        session=s,
    )
    print(f"job {ml_job.id} submitted")
    status = ml_job.wait(timeout=WAIT_SECONDS)
    s.sql(
        f"update {cfg.database}.WORKSPACE.RUN_LOG set JOB_ID = ? where RUN_ID = ? and STAGE = ? and MODEL_VERSION = ?",
        params=[ml_job.id, run_id, job, version],
    ).collect()
    logs = ml_job.get_logs() or ""
    print(logs)
    if status != "DONE":
        raise RuntimeError(f"job {ml_job.id} ended with status {status}")
    lines = [ln for ln in logs.splitlines() if ln.strip().startswith("{")]
    if not lines:
        raise RuntimeError(f"job {ml_job.id} printed no result line")
    result = json.loads(lines[-1])
    result["job_id"] = ml_job.id
    return result


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--env", required=True)
    p.add_argument("--job", required=True, choices=["train", "forecast"])
    p.add_argument("--version", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--build-dir", required=True)
    a = p.parse_args(argv)
    result = run(config.load(a.env), a.job, a.version, a.run_id, a.build_dir)
    print(json.dumps(result))
    if a.job == "train" and not result.get("gate", False):
        return 1
    print(f"##vso[task.setvariable variable=modelVersion;isOutput=true]{result['version']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
