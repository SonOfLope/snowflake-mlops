"""Score one model version, the environment's default unless one is named, and write the forecast rows. Runs inside a Snowflake ML Job."""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("LUCKML_CONFIG_DIR", str(ROOT / "config"))

import pandas as pd

from luckml import config, data, features, forecast, registry, session


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--env", required=True)
    p.add_argument("--version")
    p.add_argument("--run-id", required=True)
    a = p.parse_args(argv)
    cfg = config.load(a.env)
    s = session.connect(cfg)
    version = a.version or registry.default_version(s, cfg)
    mv = registry.get_version(s, cfg, version)
    hist = data.load_feature_frame(s, cfg)
    _, holdout = features.split_last_months(features.training_frame(hist), cfg.eval_months)
    rows = pd.concat([forecast.backfill_frame(mv, holdout), forecast.predict_horizon(mv, hist, cfg.horizon_months)])
    n = forecast.write(s, cfg, rows, version, a.run_id)
    s.sql(
        f"insert into {cfg.database}.WORKSPACE.RUN_LOG (RUN_ID, STAGE, MODEL_VERSION, MAPE, GATE_PASSED, RUN_AT) "
        "select ?, 'forecast', ?, null, true, current_timestamp()",
        params=[a.run_id, version],
    ).collect()
    print(json.dumps({"version": version, "rows": n}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
