"""Refreshes the actuals and refuses a version worse than the default beyond the tolerance. Runs inside a Snowflake ML Job."""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("LUCKML_CONFIG_DIR", str(ROOT / "config"))

from luckml import config, ops, session


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--env", required=True)
    p.add_argument("--version", required=True)
    p.add_argument("--run-id", required=True)
    a = p.parse_args(argv)
    cfg = config.load(a.env)
    ops.gate(session.connect(cfg), cfg, a.version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
