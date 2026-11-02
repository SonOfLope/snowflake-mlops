"""Train, evaluate, gate and log one model version. Runs inside a Snowflake ML Job."""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("LUCKML_CONFIG_DIR", str(ROOT / "config"))

from luckml import config, data, features, model, registry, session


def write_run_log(s, cfg, run_id, stage, version, metrics, gate_passed):
    s.sql(
        f"insert into {cfg.database}.WORKSPACE.RUN_LOG (RUN_ID, STAGE, MODEL_VERSION, MAPE, WAPE, METRICS, GATE_PASSED, RUN_AT) "
        "select ?, ?, ?, ?, ?, parse_json(?), ?, current_timestamp()",
        params=[run_id, stage, version, metrics.get("mape"), metrics.get("wape"), json.dumps(metrics), gate_passed],
    ).collect()


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--env", required=True)
    p.add_argument("--version", required=True)
    p.add_argument("--run-id", required=True)
    a = p.parse_args(argv)
    cfg = config.load(a.env)
    s = session.connect(cfg)
    if registry.version_exists(s, cfg, a.version):
        print(json.dumps({"version": a.version, "wape": None, "gate": True, "existing": True}))
        return 0
    frame = features.training_frame(data.load_feature_frame(s, cfg))
    train, holdout = features.split_last_months(frame, cfg.eval_months)
    m = model.fit(train)
    metrics = model.evaluate(m, holdout, train, cfg.risk_threshold)
    passed = model.gate(metrics, cfg)
    write_run_log(s, cfg, a.run_id, "train", a.version, metrics, passed)
    if passed:
        registry.log(s, cfg, m, a.version, metrics, train)
    print(json.dumps({"version": a.version, "gate": passed, **metrics}))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
