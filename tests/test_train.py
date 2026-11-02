import json

import pandas as pd

from jobs import train
from luckml import data, registry, session


def _bad_frame():
    months = pd.date_range("2025-01-01", periods=12, freq="MS")
    rows = []
    for site in (101, 102):
        for i, m in enumerate(months):
            tonnes = 1000.0 if i < 9 else 10.0
            rows.append(
                {"SITE_ID": site, "MONTH": m, "TONNES": tonnes, "LAG_1": 1000.0, "LAG_2": 1000.0,
                 "LAG_3": 1000.0, "MONTH_NUM": m.month}
            )
    return pd.DataFrame(rows)


def test_train_main_fails_gate_without_logging(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(session, "connect", lambda cfg: object())
    monkeypatch.setattr(data, "load_feature_frame", lambda s, cfg: _bad_frame())
    monkeypatch.setattr(registry, "version_exists", lambda s, cfg, v: False)
    monkeypatch.setattr(registry, "log", lambda *a, **k: calls.append(a))
    monkeypatch.setattr(train, "write_run_log", lambda *a, **k: None)
    rc = train.main(["--env", "dev", "--version", "VTEST", "--run-id", "t1"])
    last = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert rc == 1
    assert last["gate"] is False and last["version"] == "VTEST" and "wape" in last
    assert calls == []
