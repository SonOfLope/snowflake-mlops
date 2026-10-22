"""Score one model version on the months ahead and write the forecast rows. Runs inside a Snowflake ML Job."""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("LUCKML_CONFIG_DIR", str(ROOT / "config"))

import pandas as pd

from luckml import config, data, features, forecast, registry, session


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--env", required=True)
    p.add_argument("--version", required=True)
    p.add_argument("--run-id", required=True)
    a = p.parse_args(argv)
    cfg = config.load(a.env)
    s = session.connect(cfg)
    mv = registry.get_version(s, cfg, a.version)
    hist = data.load_feature_frame(s, cfg)
    _, holdout = features.split_last_months(features.training_frame(hist), cfg.eval_months)
    rows = pd.concat([forecast.backfill_frame(mv, holdout), forecast.predict_horizon(mv, hist, cfg.horizon_months)])
    n = forecast.write(s, cfg, rows, a.version, a.run_id)
    s.sql(
        f"insert into {cfg.database}.WORKSPACE.RUN_LOG (RUN_ID, STAGE, MODEL_VERSION, MAPE, GATE_PASSED, RUN_AT) "
        "select ?, 'forecast', ?, null, true, current_timestamp()",
        params=[a.run_id, a.version],
    ).collect()
    print(json.dumps({"version": a.version, "rows": n, "gate": True}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
